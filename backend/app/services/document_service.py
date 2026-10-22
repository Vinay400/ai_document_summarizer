"""
Document extraction (PDF / DOCX / TXT), cleaning, and storage of the text.

Pipeline
--------
`extract_text` returns what the file literally contains. `extract_and_clean`
runs that through `cleaning_service` to turn a grid of extracted lines back into
flowing prose. The upload endpoint uses the latter; `extract_text` stays public
because it is the extraction step on its own, and is tested as such.

Storage
-------
`/api/upload` processes the document once and saves the result under a
`document_id`:

    uploads/<document_id>.txt     cleaned text, UTF-8
    uploads/<document_id>.json    metadata (filename, counts, method, ...)

`/api/summarize` then sends only that id, so changing mode or length never
re-uploads the file. The original upload is deleted after extraction, because
only the text is needed from that point on.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF (the module is also importable as `pymupdf`; `fitz` is
# the long-standing name and still works, though newer releases warn about it)
from docx import Document as DocxDocument
from fastapi import HTTPException

from app.config import settings
from app.services import chunking_service, cleaning_service, ocr_service
from app.services.cleaning_service import CleanedText
from app.utils.text_utils import count_characters, count_words, has_text

logger = logging.getLogger(__name__)

# Below this many characters a document is treated as having no usable content.
# Kept small: it catches empty or garbage input, not short-but-real documents.
MIN_DOCUMENT_CHARS = 40

# Pages/paragraphs are joined with a blank line so structural boundaries survive.
# Sentence segmentation and chunking later treat blank lines as hard breaks.
BLOCK_SEPARATOR = "\n\n"


@dataclass
class ExtractionResult:
    """Raw output of an extraction pass."""

    text: str
    file_type: str
    extraction_method: str
    page_count: int | None = None
    ocr_used: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass
class OcrOutcome:
    """What happened when OCR was offered the image-only pages of a PDF.

    `attempted` distinguishes "OCR was not needed / not possible" from "OCR ran";
    `unavailable_reason` is set only when Tesseract could not be used at all, so
    the caller can tell the user how to install it.
    """

    attempted: bool
    recovered: list[int] = field(default_factory=list)
    failed: list[int] = field(default_factory=list)
    unavailable_reason: str | None = None


# --------------------------------------------------------------------------- #
# Extraction
# --------------------------------------------------------------------------- #
def extract_text(path: Path, file_type: str) -> ExtractionResult:
    """Extract text from a document, dispatching on its file type."""
    if file_type == "pdf":
        return _extract_pdf(path)
    if file_type == "docx":
        return _extract_docx(path)
    if file_type == "txt":
        return _extract_txt(path)
    raise HTTPException(status_code=400, detail=f"Cannot process '{file_type}' files.")


def extract_and_clean(path: Path, file_type: str) -> tuple[ExtractionResult, CleanedText]:
    """The ingestion pipeline: extract the raw text, then clean it.

    Extraction stays a separate function so it can be tested on its own and so
    the raw text remains available; this is the step the upload endpoint uses.
    """
    result = extract_text(path, file_type)
    return result, cleaning_service.clean_text(result.text)


def _extract_pdf(path: Path) -> ExtractionResult:
    """Read the text layer of each PDF page, falling back to OCR for images.

    PyMuPDF returns an empty string for a page that is really a picture, because
    there is no text layer to read. Any page below
    `settings.OCR_MIN_CHARS_PER_PAGE` characters is therefore treated as an image
    and handed to Tesseract; pages that already have text are never re-processed,
    so a normal digital PDF costs nothing extra.
    """
    try:
        document = fitz.open(path)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"The PDF could not be opened. It may be corrupt. ({exc})",
        )

    try:
        if document.needs_pass:
            raise HTTPException(
                status_code=422,
                detail="This PDF is password protected. Please upload an unlocked copy.",
            )

        page_count = document.page_count
        if page_count == 0:
            raise HTTPException(status_code=400, detail="The PDF contains no pages.")

        page_texts = [page.get_text("text") or "" for page in document]

        # A real page of prose has hundreds of characters; a scanned page has
        # almost none. This threshold is what decides whether OCR runs at all.
        scanned_pages = [
            number
            for number, page_text in enumerate(page_texts, start=1)
            if len(page_text.strip()) < settings.OCR_MIN_CHARS_PER_PAGE
        ]

        # OCR must happen while the document is still open: it renders pages, and
        # PyMuPDF cannot render a closed document.
        outcome = _recover_scanned_pages(document, page_texts, scanned_pages)
    finally:
        # Always release the native handle, or the temp file cannot be deleted
        # on Windows.
        document.close()

    # Joined only now, so it includes whatever OCR recovered above.
    text = BLOCK_SEPARATOR.join(page_texts)
    warnings = _pdf_warnings(page_count, scanned_pages, outcome)

    if not has_text(text):
        raise HTTPException(status_code=422, detail=_no_text_detail(outcome))

    return ExtractionResult(
        text=text,
        file_type="pdf",
        extraction_method=_pdf_method(page_count - len(scanned_pages), outcome),
        page_count=page_count,
        ocr_used=bool(outcome.recovered),
        warnings=warnings,
    )


def _recover_scanned_pages(
    document, page_texts: list[str], scanned_pages: list[int]
) -> OcrOutcome:
    """Run OCR over the image-only pages, replacing their text in `page_texts`.

    `page_texts` is mutated in place: a page whose OCR result contains real text
    overwrites its (empty) text-layer entry. Pages OCR cannot read are left
    untouched, so the caller still gets whatever text the document did have.

    OCR failure on a single page is not fatal — a mostly-digital PDF with one
    bad scan should still upload. Only a completely unavailable Tesseract is
    reported up, and even then the caller decides whether that is an error.
    """
    if not scanned_pages:
        return OcrOutcome(attempted=False)

    available, reason = ocr_service.availability()
    if not available:
        return OcrOutcome(
            attempted=False,
            failed=list(scanned_pages),
            unavailable_reason=reason,
        )

    recovered: list[int] = []
    failed: list[int] = []

    for index, number in enumerate(scanned_pages):
        try:
            page_text = ocr_service.ocr_page(document[number - 1])
        except ocr_service.OcrUnavailableError as exc:
            # Tesseract gave out part-way through (removed, or missing language
            # pack). Stop rather than retrying every remaining page.
            logger.warning("OCR stopped at page %d: %s", number, exc)
            failed.extend(scanned_pages[index:])
            return OcrOutcome(True, recovered, failed, unavailable_reason=str(exc))
        except Exception as exc:  # pragma: no cover - unexpected rendering error
            logger.warning("OCR failed on page %d: %s", number, exc)
            failed.append(number)
            continue

        if has_text(page_text):
            page_texts[number - 1] = page_text.strip()
            recovered.append(number)
        else:
            failed.append(number)

    logger.info(
        "OCR recovered %d of %d image-only page(s)", len(recovered), len(scanned_pages)
    )
    return OcrOutcome(attempted=True, recovered=recovered, failed=failed)


def _pdf_method(text_layer_pages: int, outcome: OcrOutcome) -> str:
    """Describe how the text was obtained, for display in the UI.

    Keyed on whether any page had a real text layer, not on how many pages OCR
    recovered: a fully scanned PDF whose OCR partly failed is still an OCR
    extraction, and saying "PyMuPDF text layer" there would be a lie.
    """
    if not outcome.recovered:
        return "PyMuPDF text layer"
    if text_layer_pages == 0:
        return f"Tesseract OCR ({len(outcome.recovered)} page(s))"
    return f"PyMuPDF text layer + Tesseract OCR ({len(outcome.recovered)} page(s))"


def _pdf_warnings(
    page_count: int, scanned_pages: list[int], outcome: OcrOutcome
) -> list[str]:
    """Non-fatal notes the user should see about how the PDF was read."""
    warnings: list[str] = []

    if not scanned_pages:
        return warnings

    listed = ", ".join(str(n) for n in scanned_pages[:10])
    if len(scanned_pages) > 10:
        listed += ", ..."

    if outcome.attempted:
        if outcome.recovered:
            warnings.append(
                f"{len(outcome.recovered)} of {page_count} page(s) had no text "
                f"layer and were read with OCR: page {listed}. OCR output may "
                "contain recognition errors."
            )
        if outcome.failed:
            warnings.append(
                f"OCR produced no readable text for {len(outcome.failed)} page(s): "
                f"page {', '.join(str(n) for n in outcome.failed[:10])}. "
                "The summary will be based on the remaining pages."
            )
    else:
        warnings.append(
            f"{len(scanned_pages)} of {page_count} page(s) appear to be images and "
            f"were skipped because OCR is unavailable ({outcome.unavailable_reason}). "
            "Text from the remaining pages has been used. See the README for how "
            "to install Tesseract."
        )

    return warnings


def _no_text_detail(outcome: OcrOutcome) -> str:
    """Explain a PDF that yielded nothing, with the right remedy for the cause."""
    if outcome.unavailable_reason:
        return (
            "This PDF contains no text layer (every page is a scanned image) "
            f"and OCR could not run: {outcome.unavailable_reason}. Install "
            "Tesseract (see the README) or set TESSERACT_CMD in the backend .env, "
            "then upload the file again."
        )
    if outcome.attempted:
        return (
            "No readable text could be extracted. Every page is an image, and OCR "
            "did not recognise any text in them. The scan may be too low-quality "
            "or in a language that is not configured (OCR_LANGUAGE)."
        )
    return (
        "No text layer was found in this PDF, and no images were detected to run "
        "OCR on."
    )


def _extract_docx(path: Path) -> ExtractionResult:
    """Read paragraphs and tables from a DOCX file.

    Headers and footers are skipped on purpose: they repeat on every page, so
    including them would duplicate the same lines many times.
    """
    try:
        document = DocxDocument(str(path))
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                "The DOCX file could not be read. It may be corrupt, or it may "
                f"be a legacy .doc file renamed to .docx. ({exc})"
            ),
        )

    blocks = [p.text.strip() for p in document.paragraphs if p.text.strip()]

    # Tables often hold the substance of a report (results, metrics).
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                blocks.append(" | ".join(cells))

    text = BLOCK_SEPARATOR.join(blocks)

    if not has_text(text):
        raise HTTPException(
            status_code=400,
            detail=(
                "No readable text was found in the DOCX file. If the content is "
                "inside images, it cannot be extracted without OCR."
            ),
        )

    return ExtractionResult(
        text=text,
        file_type="docx",
        extraction_method="python-docx (paragraphs and tables)",
        # python-docx has no layout engine, so page breaks are unknowable.
        page_count=None,
        ocr_used=False,
    )


def _extract_txt(path: Path) -> ExtractionResult:
    """Read a text file, tolerating the encodings Windows editors produce."""
    raw = path.read_bytes()

    # utf-8-sig also strips a byte-order mark. latin-1 maps every byte value, so
    # it always succeeds as the final fallback.
    text, encoding = "", "utf-8"
    for candidate in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text, encoding = raw.decode(candidate), candidate
            break
        except UnicodeDecodeError:
            continue

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    if not has_text(text):
        raise HTTPException(status_code=400, detail="The text file is empty.")

    warnings = []
    if encoding not in ("utf-8-sig", "utf-8"):
        warnings.append(
            f"The file was not valid UTF-8 and was decoded as {encoding}; "
            "some characters may be misread."
        )

    return ExtractionResult(
        text=text,
        file_type="txt",
        extraction_method=f"plain text ({encoding})",
        page_count=None,
        ocr_used=False,
        warnings=warnings,
    )


# --------------------------------------------------------------------------- #
# Storage
# --------------------------------------------------------------------------- #
def _text_file(document_id: str) -> Path:
    return settings.upload_dir / f"{document_id}.txt"


def _meta_file(document_id: str) -> Path:
    return settings.upload_dir / f"{document_id}.json"


def build_metadata(
    document_id: str,
    filename: str,
    result: ExtractionResult,
    cleaned: CleanedText,
) -> dict:
    """Assemble the public metadata for an ingested document (no text).

    Counts describe the *cleaned* text, because that is what gets stored and
    summarized; the raw size is reported separately under `cleaning` so the
    effect of cleaning stays visible.
    """
    return {
        "document_id": document_id,
        "filename": filename,
        "file_type": result.file_type,
        "character_count": count_characters(cleaned.text),
        "word_count": count_words(cleaned.text),
        "chunk_count": len(chunking_service.chunk_text(cleaned.text)),
        "page_count": result.page_count,
        "ocr_used": result.ocr_used,
        "extraction_method": result.extraction_method,
        "cleaning": {
            "raw_character_count": cleaned.original_character_count,
            "removed_line_count": cleaned.removed_line_count,
            "hyphenation_joins": cleaned.hyphenation_joins,
        },
    }


def save_document(document_id: str, text: str, metadata: dict) -> None:
    """Persist the extracted text and its metadata."""
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    _text_file(document_id).write_text(text, encoding="utf-8")
    _meta_file(document_id).write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def load_document(document_id: str) -> tuple[str, dict]:
    """Return `(text, metadata)` for a stored document.

    Raises 404 if it is missing — which is also what the user sees after the
    server restarts with a cleared uploads directory.
    """
    meta_file, text_file = _meta_file(document_id), _text_file(document_id)

    if not meta_file.exists() or not text_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Document not found or no longer available. Please upload it again.",
        )

    return text_file.read_text(encoding="utf-8"), json.loads(
        meta_file.read_text(encoding="utf-8")
    )


def document_exists(document_id: str) -> bool:
    return _meta_file(document_id).exists() and _text_file(document_id).exists()
