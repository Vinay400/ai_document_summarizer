"""System health and readiness endpoints."""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import settings
from app.services import ocr_service

router = APIRouter(tags=["System"])


@router.get("/health", summary="Liveness / readiness probe")
async def health_check() -> dict:
    """Report that the API process is up and how it is configured.

    The front-end calls this on load so the UI can tell the user immediately
    whether the backend is reachable, instead of failing later with a confusing
    upload error.
    """
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "python_version": sys.version.split()[0],
        "platform": platform.system(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ocr": _ocr_status(),
    }


def _ocr_status() -> dict:
    """Describe whether scanned-PDF support is usable.

    A health endpoint must not be the thing that fails, so any error while
    probing Tesseract (or importing the wrapper) is reported as data rather than
    raised. OCR is optional: the API is healthy without it, it just cannot read
    scanned documents.
    """
    try:
        available, reason = ocr_service.availability()
    except Exception as exc:  # pragma: no cover - defensive
        available, reason = False, f"OCR status could not be determined ({exc})"

    status = {"available": available, "language": settings.OCR_LANGUAGE}
    if reason:
        status["reason"] = reason
    return status
