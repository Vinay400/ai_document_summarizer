"""Endpoint tests: health reporting and the upload -> extract flow.

Uploads land in a temporary directory (see the `client` fixture in conftest), so
the real `uploads/` folder is never touched.
"""

import pytest

from app.config import settings
from app.services import ocr_service


def _upload(client, fixtures_dir, name, content_type):
    with (fixtures_dir / name).open("rb") as handle:
        return client.post(
            "/api/upload", files={"file": (name, handle, content_type)}
        )


def test_health_reports_ocr_status(client):
    body = client.get("/api/health").json()

    assert body["status"] == "ok"
    assert body["ocr"]["language"] == settings.OCR_LANGUAGE
    assert isinstance(body["ocr"]["available"], bool)
    # A missing Tesseract is not an unhealthy API, so it must not be a failure.
    if not body["ocr"]["available"]:
        assert body["ocr"]["reason"]


def test_upload_txt_returns_metadata_and_never_the_text(client, fixtures_dir):
    response = _upload(client, fixtures_dir, "sample.txt", "text/plain")

    assert response.status_code == 200
    body = response.json()
    assert body["file_type"] == "txt"
    assert body["word_count"] > 0
    assert body["preview"]
    # The document stays server-side; only its id travels back.
    assert "text" not in body
    assert body["document_id"]


def test_upload_rejects_unsupported_extension(client):
    response = client.post(
        "/api/upload", files={"file": ("photo.png", b"\x89PNG", "image/png")}
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_rejects_empty_file(client):
    response = client.post(
        "/api/upload", files={"file": ("empty.txt", b"", "text/plain")}
    )

    assert response.status_code == 400


def test_upload_scanned_pdf_follows_ocr_availability(client, fixtures_dir):
    """The outcome of a scanned upload depends only on whether OCR can run."""
    response = _upload(client, fixtures_dir, "scanned.pdf", "application/pdf")

    if ocr_service.is_available():
        assert response.status_code == 200
        assert response.json()["ocr_used"] is True
    else:
        assert response.status_code == 422
        assert "Tesseract" in response.json()["detail"]


def test_upload_reports_cleaning_and_chunking(client, fixtures_dir):
    response = _upload(client, fixtures_dir, "sample.pdf", "application/pdf")

    assert response.status_code == 200
    body = response.json()

    assert body["chunk_count"] >= 1
    cleaning = body["cleaning"]
    # The raw text is always at least as long as what survived cleaning.
    assert cleaning["raw_character_count"] >= body["character_count"]
    assert cleaning["hyphenation_joins"] >= 0
    assert cleaning["removed_line_count"] >= 0


def test_upload_stores_cleaned_text_not_raw(client):
    """The cleaning step must be reflected in what the user gets back."""
    content = (
        "Confidential\n"
        "Page 1 of 3\n"
        "summa-\n"
        "rization is the task.\n"
        "\n"
        "Confidential\n"
        "Page 2 of 3\n"
        "The model is large.\n"
        "\n"
        "Confidential\n"
        "Page 3 of 3\n"
        "The end.\n"
    )
    response = client.post(
        "/api/upload", files={"file": ("doc.txt", content.encode(), "text/plain")}
    )

    assert response.status_code == 200
    body = response.json()

    assert body["cleaning"]["hyphenation_joins"] == 1
    # Three repeated headers plus three page numbers.
    assert body["cleaning"]["removed_line_count"] == 6
    assert "summarization is the task." in body["preview"]
    assert "Page 1 of 3" not in body["preview"]
    assert "Confidential" not in body["preview"]
