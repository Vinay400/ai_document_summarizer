"""Extraction tests for every supported file type, plus the OCR fallback.

The OCR tests come in two flavours:

* behaviour that must hold whether or not Tesseract is installed (a scanned PDF
  is either read, or rejected with a message that says how to install it);
* tests that need real OCR, skipped when the binary is absent so the suite
  stays green on a machine without it.
"""

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.services import document_service, ocr_service

requires_tesseract = pytest.mark.skipif(
    not ocr_service.is_available(),
    reason="Tesseract is not installed (it is not a pip package - see the README)",
)


def _extract(path: Path, file_type: str | None = None):
    return document_service.extract_text(path, file_type or path.suffix.lstrip("."))


def _mixed_pdf(tmp_path: Path) -> Path:
    """A PDF with one real text page and one image-only page.

    The text page must comfortably exceed OCR_MIN_CHARS_PER_PAGE (80 by
    default), otherwise it would itself be classified as an image and the
    fixture would stop testing what it claims to.

    The image page must contain *actual* legible pixels. A blank image would let
    the stubbed tests pass while real OCR correctly found nothing, so the
    geometry below mirrors `make_fixtures.write_scanned_pdf`, which real
    Tesseract is known to read.
    """
    import fitz
    from PIL import Image, ImageDraw

    image_path = tmp_path / "scan.png"
    image = Image.new("RGB", (1200, 400), "white")
    draw = ImageDraw.Draw(image)
    draw.text(
        (30, 40),
        "This page is an image. Optical character recognition is required "
        "to read it.",
        fill="black",
    )
    image.save(image_path)

    document = fitz.open()
    text_page = document.new_page()
    text_page.insert_textbox(
        fitz.Rect(50, 50, 545, 400),
        "This digital page carries a real text layer of its own, long enough to "
        "be recognised as prose rather than as a scanned image, so the extractor "
        "must read it directly instead of rendering it for OCR.",
        fontsize=11,
    )
    image_page = document.new_page(width=595, height=300)
    image_page.insert_image(image_page.rect, filename=str(image_path))

    path = tmp_path / "mixed.pdf"
    document.save(path)
    document.close()
    return path


# --------------------------------------------------------------------------- #
# Non-OCR extraction (Phases 2-3 regression coverage)
# --------------------------------------------------------------------------- #
def test_txt_is_decoded(fixtures_dir):
    result = _extract(fixtures_dir / "sample.txt")
    assert result.file_type == "txt"
    assert "summarization" in result.text
    assert result.ocr_used is False
    assert result.warnings == []


def test_docx_reads_paragraphs_and_tables(fixtures_dir):
    result = _extract(fixtures_dir / "sample.docx")
    assert result.file_type == "docx"
    assert "ROUGE" in result.text  # only present in the table
    assert result.page_count is None  # page breaks are unknowable for DOCX


def test_pdf_text_layer_is_used_without_ocr(fixtures_dir):
    result = _extract(fixtures_dir / "sample.pdf")
    assert result.page_count == 3
    assert result.ocr_used is False
    assert result.extraction_method == "PyMuPDF text layer"
    assert result.warnings == []


def test_empty_txt_is_rejected(fixtures_dir):
    with pytest.raises(HTTPException) as exc:
        _extract(fixtures_dir / "empty.txt")
    assert exc.value.status_code == 400


def test_unsupported_type_is_rejected(tmp_path):
    path = tmp_path / "notes.md"
    path.write_text("hello", encoding="utf-8")
    with pytest.raises(HTTPException) as exc:
        document_service.extract_text(path, "md")
    assert exc.value.status_code == 400


# --------------------------------------------------------------------------- #
# The full ingestion pipeline: extract, then clean
# --------------------------------------------------------------------------- #
def test_extract_and_clean_keeps_the_raw_text_addressable(fixtures_dir):
    result, cleaned = document_service.extract_and_clean(
        fixtures_dir / "sample.txt", "txt"
    )

    assert result.text  # the raw extraction is still returned
    assert cleaned.text
    assert cleaned.original_character_count == len(result.text)


def test_pdf_line_wraps_are_reflowed(fixtures_dir):
    """The reason cleaning exists: a PDF page is a grid of meaningless lines."""
    result, cleaned = document_service.extract_and_clean(
        fixtures_dir / "sample.pdf", "pdf"
    )

    # Extraction wraps each line, so single newlines are everywhere...
    assert "\n" in result.text
    # ...and cleaning leaves only the paragraph breaks.
    assert "\n" not in cleaned.text.replace("\n\n", "")
    assert cleaned.character_count > 0


def test_cleaning_is_reported_in_the_metadata(fixtures_dir):
    result, cleaned = document_service.extract_and_clean(
        fixtures_dir / "sample.txt", "txt"
    )

    metadata = document_service.build_metadata("abc123", "sample.txt", result, cleaned)

    assert metadata["character_count"] == len(cleaned.text)
    assert metadata["word_count"] == len(cleaned.text.split())
    assert metadata["chunk_count"] >= 1
    assert metadata["cleaning"]["raw_character_count"] == len(result.text)
    assert metadata["extraction_method"] == result.extraction_method
# --------------------------------------------------------------------------- #
# Scanned PDFs when Tesseract is NOT available
# --------------------------------------------------------------------------- #
def test_all_image_pdf_fails_with_install_guidance(fixtures_dir, monkeypatch):
    """No text layer and no OCR: fail, but tell the user how to fix it."""
    monkeypatch.setattr(ocr_service, "availability", lambda: (False, "not installed"))

    with pytest.raises(HTTPException) as exc:
        _extract(fixtures_dir / "scanned.pdf")

    assert exc.value.status_code == 422
    assert "Tesseract" in exc.value.detail
    assert "not installed" in exc.value.detail


def test_mixed_pdf_warns_but_still_extracts_text(tmp_path, monkeypatch):
    """One unreadable page must not cost the user the readable ones."""
    monkeypatch.setattr(ocr_service, "availability", lambda: (False, "not installed"))

    result = _extract(_mixed_pdf(tmp_path))

    assert result.ocr_used is False
    assert "real text layer" in result.text
    assert any("OCR is unavailable" in warning for warning in result.warnings)


# --------------------------------------------------------------------------- #
# OCR orchestration, verified without the Tesseract binary
#
# Only the recognition step is stubbed; availability, page rendering and the
# merging of results all run for real. This keeps the wiring covered on every
# machine, while the tests below cover real recognition quality where possible.
# --------------------------------------------------------------------------- #
def _stub_tesseract(monkeypatch, text: str = "Text recovered by OCR.") -> None:
    monkeypatch.setattr(ocr_service, "availability", lambda: (True, None))
    monkeypatch.setattr(
        ocr_service.pytesseract, "image_to_string", lambda image, **kwargs: text
    )


def test_stubbed_ocr_reads_a_fully_scanned_pdf(fixtures_dir, monkeypatch):
    _stub_tesseract(monkeypatch, "A scanned paragraph recovered by OCR.")

    result = _extract(fixtures_dir / "scanned.pdf")

    assert result.ocr_used is True
    assert result.page_count == 2
    assert result.extraction_method == "Tesseract OCR (2 page(s))"
    assert "recovered by OCR" in result.text
    # Every page was an image, so all of them should be replaced.
    assert result.text.count("recovered by OCR") == 2


def test_stubbed_ocr_only_touches_the_image_pages(tmp_path, monkeypatch):
    """/api/pdf mixed: the digital page keeps its own text, not the OCR output."""
    _stub_tesseract(monkeypatch, "Stubbed OCR output.")

    result = _extract(_mixed_pdf(tmp_path))

    assert result.ocr_used is True
    assert result.page_count == 2
    assert result.extraction_method == "PyMuPDF text layer + Tesseract OCR (1 page(s))"
    # The real text layer survives untouched...
    assert "real text layer" in result.text
    # ...and the image page was filled in by OCR.
    assert "Stubbed OCR output." in result.text
    assert any("read with OCR" in warning for warning in result.warnings)


def test_stubbed_ocr_that_finds_nothing_fails_clearly(fixtures_dir, monkeypatch):
    """OCR ran but recognised nothing: report that, not the install message."""
    _stub_tesseract(monkeypatch, "   \n  ")

    with pytest.raises(HTTPException) as exc:
        _extract(fixtures_dir / "scanned.pdf")

    assert exc.value.status_code == 422
    assert "did not recognise any text" in exc.value.detail


def test_ocr_failure_mid_document_is_not_fatal(fixtures_dir, monkeypatch):
    """If Tesseract dies part-way, the text already recovered is still used."""
    from app.services.ocr_service import OcrUnavailableError

    monkeypatch.setattr(ocr_service, "availability", lambda: (True, None))

    calls = {"n": 0}

    def flaky(image, **kwargs):
        calls["n"] += 1
        if calls["n"] > 1:
            raise OcrUnavailableError("language pack vanished")
        return "First page recovered."

    monkeypatch.setattr(ocr_service.pytesseract, "image_to_string", flaky)

    # scanned.pdf has two image-only pages, so page 2 is where OCR gives out.
    result = _extract(fixtures_dir / "scanned.pdf")

    assert "First page recovered." in result.text
    assert any("no readable text for" in warning for warning in result.warnings)
    # Recognised as OCR, not as a text layer - there was never a text layer here.
    assert result.extraction_method == "Tesseract OCR (1 page(s))"


# --------------------------------------------------------------------------- #
# Scanned PDFs when Tesseract IS available
# --------------------------------------------------------------------------- #
@requires_tesseract
def test_scanned_pdf_is_read_with_ocr(fixtures_dir):
    result = _extract(fixtures_dir / "scanned.pdf")

    assert result.ocr_used is True
    assert result.page_count == 2
    assert "Tesseract OCR" in result.extraction_method
    # Assert structure, not exact wording: OCR of the fixture's bitmap font can
    # misread individual characters.
    assert len(result.text.split()) >= 10
    assert any(word.isalpha() and len(word) > 3 for word in result.text.split())


@requires_tesseract
def test_mixed_pdf_uses_both_paths(tmp_path):
    result = _extract(_mixed_pdf(tmp_path))

    assert result.ocr_used is True
    assert "real text layer" in result.text  # from the digital page
    assert "PyMuPDF text layer + Tesseract OCR" in result.extraction_method
