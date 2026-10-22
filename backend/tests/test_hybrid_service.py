"""Phase 7 tests: hybrid summarization service (TextRank filtering + BART abstractive).

Follows test_summarize.py structure: module-scoped fixture reading tests/fixtures/sample.txt.
"""

import pytest

from app.services import hybrid_service


@pytest.fixture(scope="module")
def document(fixtures_dir):
    return (fixtures_dir / "sample.txt").read_text(encoding="utf-8")


def test_short_document_returns_unchanged():
    text = "Short text."
    assert hybrid_service.summarize(text) == text.strip()


@pytest.mark.slow
def test_hybrid_summary_is_non_empty_and_shorter_than_source(document):
    summary = hybrid_service.summarize(document, length="medium")
    assert summary.strip()
    assert len(summary) < len(document)


@pytest.mark.slow
def test_hybrid_endpoint_call(client, fixtures_dir):
    with (fixtures_dir / "sample.txt").open("rb") as handle:
        uploaded = client.post(
            "/api/upload", files={"file": ("sample.txt", handle, "text/plain")}
        ).json()

    response = client.post(
        "/api/summarize",
        json={
            "document_id": uploaded["document_id"],
            "mode": "hybrid",
            "length": "medium",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "hybrid"
    assert body["summary"].strip()
