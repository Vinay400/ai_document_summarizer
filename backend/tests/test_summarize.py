"""Phase 5: extractive summarization and the /api/summarize endpoint.

These tests load the embedding model, which downloads ~90 MB the first time.
"""

import pytest

from app.services import extractive_service
from app.services.chunking_service import split_sentences


@pytest.fixture(scope="module")
def document(fixtures_dir):
    return (fixtures_dir / "sample.txt").read_text(encoding="utf-8")


def test_summary_is_shorter_than_the_source(document):
    for length in ("short", "medium", "long"):
        assert len(extractive_service.summarize(document, length)) < len(document)


def test_longer_lengths_produce_longer_summaries(document):
    short = extractive_service.summarize(document, "short")
    long = extractive_service.summarize(document, "long")

    assert len(short) < len(long)


def test_every_summary_sentence_is_quoted_from_the_source(document):
    """The defining property of extractive summarization: nothing is invented."""
    source = set(split_sentences(document))

    summary = extractive_service.summarize(document, "medium")

    assert split_sentences(summary)
    for sentence in split_sentences(summary):
        assert sentence in source, f"not from the source: {sentence!r}"


def test_a_short_document_is_returned_unchanged():
    text = "Only one sentence here."

    assert extractive_service.summarize(text) == text


def test_summarize_endpoint_returns_a_summary(client, fixtures_dir):
    with (fixtures_dir / "sample.txt").open("rb") as handle:
        uploaded = client.post(
            "/api/upload", files={"file": ("sample.txt", handle, "text/plain")}
        ).json()

    response = client.post(
        "/api/summarize",
        json={"document_id": uploaded["document_id"], "mode": "extractive"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "extractive"
    assert body["summary"].strip()
    assert len(body["summary"]) < uploaded["character_count"]


def test_summarize_unknown_document_is_404(client):
    response = client.post(
        "/api/summarize", json={"document_id": "does-not-exist"}
    )

    assert response.status_code == 404


def test_all_supported_modes_are_registered_in_summarizers():
    """Abstractive and hybrid are now implemented in phases 6-7."""
    from app.api.summarize import SUMMARIZERS

    for mode in ("extractive", "abstractive", "hybrid"):
        assert mode in SUMMARIZERS


def test_an_unknown_mode_is_rejected_by_validation(client):
    response = client.post(
        "/api/summarize", json={"document_id": "x", "mode": "made-up"}
    )

    assert response.status_code == 422
