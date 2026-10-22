"""
POST /api/upload - ingest a PDF, DOCX or TXT document.

Flow:
    validate filename and extension
      -> save to a temporary file with a size limit
      -> extract text (PyMuPDF / python-docx / plain read, with OCR for scans)
      -> clean it into flowing prose
      -> store the cleaned text under a document id
      -> delete the temporary upload
"""

import logging

from fastapi import APIRouter, File, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.models.schemas import ErrorResponse, UploadResponse
from app.services import document_service
from app.utils.file_utils import (
    get_file_type,
    new_document_id,
    remove_file,
    safe_filename,
    save_upload,
)
from app.utils.text_utils import make_preview

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Documents"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or empty file"},
        413: {"model": ErrorResponse, "description": "File too large"},
        422: {"model": ErrorResponse, "description": "File could not be parsed"},
    },
    summary="Upload a document and extract its text",
)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    filename = safe_filename(file.filename)
    file_type = get_file_type(filename)

    document_id = new_document_id()
    temp_path = settings.upload_dir / f"{document_id}.{file_type}"

    try:
        await save_upload(file, temp_path)

        # Extraction and cleaning are blocking CPU/IO work. Running them in a
        # worker thread keeps the event loop free so /api/health and other
        # requests stay responsive while a large document is processed.
        result, cleaned = await run_in_threadpool(
            document_service.extract_and_clean, temp_path, file_type
        )
    finally:
        # The original binary is never needed again: only its text is stored.
        remove_file(temp_path)

    metadata = document_service.build_metadata(document_id, filename, result, cleaned)
    document_service.save_document(document_id, cleaned.text, metadata)

    logger.info(
        "Uploaded %s (%s): %d words, %d chunk(s), %s page(s)",
        filename,
        file_type,
        metadata["word_count"],
        metadata["chunk_count"],
        metadata["page_count"],
    )

    return UploadResponse(
        **metadata,
        preview=make_preview(cleaned.text),
        warnings=result.warnings,
    )
