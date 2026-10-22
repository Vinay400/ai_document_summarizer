"""
Tesseract OCR fallback for PDF pages that carry no text layer.

Why this exists
---------------
A scanned PDF stores each page as a picture. PyMuPDF reads the text layer and
finds nothing, because there is no text layer — the characters exist only as
pixels. Tesseract recovers them from a rendered image of the page.

This module is called only for pages whose text layer came back (nearly) empty,
so a normal digital PDF never pays the cost of rendering and OCR: see
`document_service._extract_pdf`.

Tesseract is an external program, not a pip package
---------------------------------------------------
`pip install pytesseract` installs the *wrapper*; the `tesseract` executable
must be installed separately (see the root README). The two can disagree:
importing this module always succeeds, but OCR only works if the binary can be
found.

That is why nothing here raises at import time and why `availability()` exists:
callers ask first and can return a message telling the user how to fix it,
rather than failing with a 500 somewhere deep in the stack.
"""

import logging

import pytesseract
from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)


class OcrUnavailableError(RuntimeError):
    """The Tesseract binary could not be located, started or used."""


# Probing for the binary spawns a subprocess, so the answer is cached. `None`
# means "not checked yet" — deliberately not computed at import time, so that
# importing this module has no side effects and costs nothing.
_available: bool | None = None
_reason: str | None = None


def _configure() -> None:
    """Point pytesseract at a specific binary when one is configured.

    Needed when Tesseract was installed somewhere its installer did not add to
    PATH — which is the normal situation on Windows.
    """
    if settings.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


def availability() -> tuple[bool, str | None]:
    """Return `(available, reason)`; `reason` is `None` when OCR can run.

    The result is cached after the first call. Restarting the server (or
    installing Tesseract and calling `reset_cache()`) re-probes.
    """
    global _available, _reason
    if _available is not None:
        return _available, _reason

    _configure()
    try:
        version = pytesseract.get_tesseract_version()
        logger.info("Tesseract %s available for OCR", version)
        _available, _reason = True, None
    except pytesseract.TesseractNotFoundError:
        _available = False
        _reason = (
            f"the Tesseract program could not be started from "
            f"TESSERACT_CMD='{settings.TESSERACT_CMD}'"
            if settings.TESSERACT_CMD
            else "the Tesseract program is not installed or is not on PATH"
        )
    except Exception as exc:  # pragma: no cover - environment specific
        _available, _reason = False, f"the Tesseract check failed ({exc})"

    if not _available:
        logger.warning("OCR is unavailable: %s", _reason)

    return _available, _reason


def is_available() -> bool:
    """True if OCR can actually run right now."""
    return availability()[0]


def reset_cache() -> None:
    """Forget the cached probe. Exists so tests can re-check after a change."""
    global _available, _reason
    _available, _reason = None, None


def render_page(page) -> Image.Image:
    """Rasterise a PDF page for OCR at the configured DPI.

    `alpha=False` guarantees three bytes per pixel, so the buffer maps onto
    Pillow's "RGB" mode without an extra conversion. DPI matters: at the default
    72 DPI Tesseract misreads small text, which is why OCR_DPI defaults to 200.
    """
    pixmap = page.get_pixmap(dpi=settings.OCR_DPI, alpha=False)
    return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def ocr_page(page) -> str:
    """Render one PDF page and return the text Tesseract reads from it.

    Raises `OcrUnavailableError` if Tesseract cannot be used at all. A page that
    simply contains no legible text yields an empty string, which is not an
    error — the caller decides what that means.
    """
    available, reason = availability()
    if not available:
        raise OcrUnavailableError(reason or "Tesseract is unavailable.")

    image = render_page(page)

    try:
        return pytesseract.image_to_string(image, lang=settings.OCR_LANGUAGE)
    except pytesseract.TesseractError as exc:
        # e.g. the requested language pack is not installed.
        raise OcrUnavailableError(
            f"Tesseract could not process the page (language "
            f"'{settings.OCR_LANGUAGE}'): {exc}"
        ) from exc
