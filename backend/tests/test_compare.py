"""Tests for the 3-Way Mode Comparison endpoints:
- POST /api/summarize/compare
- POST /api/evaluate/compare
"""

import pytest


def _upload_sample(client):
    content = (
        "Artificial Intelligence document summarization automates the extraction of key concepts. "
        "Extractive systems select salient sentences directly from the text without alteration. "
        "Abstractive summarization employs deep sequence-to-sequence neural architectures to synthesize concepts. "
        "Hybrid pipelines pre-filter text using graph ranking algorithms like TextRank before neural condensation. "
        "This architectural paradigm combines high factual fidelity with fluent readability for long-form reports."
    )
    res = client.post(
        "/api/upload", files={"file": ("ai_doc.txt", content.encode("utf-8"), "text/plain")}
    )
    assert res.status_code == 200
    return res.json()["document_id"]


def test_compare_summarize_unknown_doc_is_404(client):
    response = client.post(
        "/api/summarize/compare", json={"document_id": "nonexistent-doc-id"}
    )
    assert response.status_code == 404


def test_compare_summarize_endpoint(client, monkeypatch):
    """Test /api/summarize/compare with mocked fast summarizers to verify contract."""
    from app.api import summarize

    mock_summarizers = {
        "extractive": lambda text, length="medium": "Extractive mock summary of key facts.",
        "abstractive": lambda text, length="medium": "Abstractive mock summary generated cleanly.",
        "hybrid": lambda text, length="medium": "Hybrid mock summary balancing both.",
    }
    monkeypatch.setattr(summarize, "SUMMARIZERS", mock_summarizers)

    doc_id = _upload_sample(client)

    response = client.post(
        "/api/summarize/compare",
        json={"document_id": doc_id, "length": "medium"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc_id
    assert data["length"] == "medium"
    assert data["original_word_count"] > 0
    assert "extractive" in data["modes"]
    assert "abstractive" in data["modes"]
    assert "hybrid" in data["modes"]

    for mode_name in ("extractive", "abstractive", "hybrid"):
        mode_data = data["modes"][mode_name]
        assert mode_data["mode"] == mode_name
        assert mode_data["summary"].strip()
        assert mode_data["word_count"] > 0
        assert mode_data["compression_ratio"] >= 0.0
        assert "latency_seconds" in mode_data


def test_compare_evaluate_with_precomputed_summaries(client):
    """Test /api/evaluate/compare reusing already generated summaries."""
    doc_id = _upload_sample(client)

    precomputed = {
        "extractive": "Artificial Intelligence document summarization automates key concepts.",
        "abstractive": "AI summarizers generate fluent and coherent overviews.",
        "hybrid": "AI summarization uses hybrid graph and neural pipelines.",
    }

    reference = "AI document summarization condenses long text into key concepts."

    response = client.post(
        "/api/evaluate/compare",
        json={
            "document_id": doc_id,
            "reference": reference,
            "length": "medium",
            "summaries": precomputed,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc_id
    assert data["reference"] == reference
    assert "extractive" in data["modes"]
    assert "abstractive" in data["modes"]
    assert "hybrid" in data["modes"]

    for mode_name in ("extractive", "abstractive", "hybrid"):
        m_eval = data["modes"][mode_name]
        assert m_eval["mode"] == mode_name
        assert m_eval["metrics"]["rouge_1"] > 0.0
        assert m_eval["metrics"]["rouge_2"] >= 0.0
        assert m_eval["metrics"]["rouge_l"] > 0.0
        assert m_eval["metrics"]["bleu"] >= 0.0
