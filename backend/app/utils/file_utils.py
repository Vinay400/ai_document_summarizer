"""Upload helpers: filename safety, extension checks and writing to disk."""

import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings

# Only these characters survive in a display filename.
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def safe_filename(raw_name: str | None) -> str:
    """Reduce a client-supplied filename to a safe basename.

    Strips directory components (so `../../etc/passwd` becomes `passwd`) and
    replaces unsafe characters. The result is only ever used for display —
    files on disk are named after a generated id, so a hostile filename cannot
    influence any path we actually write to.
    """
    if not raw_name or not raw_name.strip():
        raise HTTPException(status_code=400, detail="No filename was provided.")

    name = raw_name.replace("\\", "/").split("/")[-1].strip()
    name = _UNSAFE.sub("_", name).lstrip(".")

    if not name:
        raise HTTPException(status_code=400, detail="The uploaded filename is not usable.")

    return name[:120]


def get_file_type(filename: str) -> str:
    """Return 'pdf' / 'docx' / 'txt', or reject the upload with HTTP 400."""
    extension = Path(filename).suffix.lower()
    allowed = settings.allowed_extensions

    if extension not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{extension or 'none'}'. "
                f"Allowed types: {', '.join(sorted(allowed))}."
            ),
        )

    return extension.lstrip(".")


def new_document_id() -> str:
    """Random id used both as the on-disk name and as the API handle."""
    return uuid.uuid4().hex


async def save_upload(file: UploadFile, destination: Path) -> int:
    """Write the upload to disk and return its size in bytes.

    The size limit is applied to the bytes actually received, so an upload that
    under-reports its length is still stopped. A rejected upload is deleted
    rather than left behind.
    """
    data = await file.read()
    size = len(data)

    if size == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    if size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File is {size / 1024 / 1024:.1f} MB, which exceeds the "
                f"{settings.MAX_FILE_SIZE_MB} MB limit. Raise MAX_FILE_SIZE_MB "
                "in the backend .env file to allow larger documents."
            ),
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return size


def remove_file(path: Path) -> None:
    """Delete a file if it exists. Never raises."""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
