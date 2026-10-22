"""Phase 8b/8c tests: evaluation service and /api/evaluate endpoint.

Evaluation tests require no deep learning models (pure string in, scores out).
"""

import pytest

from app.services import evaluation_service


def test_identical_texts_yield_perfect_scores():
    text = "This is a complete sentence used for testing evaluation metrics in python."
    scores = evaluation_service.evaluate(text, text)

    assert scores["rouge_1"] == 1.0
    assert scores["rouge_2"] == 1.0
    assert scores["rouge_l"] == 1.0
    assert pytest.approx(scores["bleu"], abs=1e-3) == 100.0


def test_completely_different_texts_yield_low_scores():
    summary = "The quick brown fox jumps over the lazy dog."
    reference = "Quantum computing relies on qubits and superposition principles."
    scores = evaluation_service.evaluate(summary, reference)

    assert scores["rouge_1"] < 0.5
    assert scores["bleu"] < 10.0


def test_empty_input_returns_zero_scores():
    scores = evaluation_service.evaluate("", "Some reference text.")
    assert scores["rouge_1"] == 0.0
    assert scores["bleu"] == 0.0


def test_evaluate_endpoint_returns_metrics(client, fixtures_dir):
    with (fixtures_dir / "sample.txt").open("rb") as handle:
        uploaded = client.post(
            "/api/upload", files={"file": ("sample.txt", handle, "text/plain")}
        ).json()

    reference_text = (fixtures_dir / "sample.txt").read_text(encoding="utf-8")[:200]

    response = client.post(
        "/api/evaluate",
        json={
            "document_id": uploaded["document_id"],
            "reference": reference_text,
            "mode": "extractive",
            "length": "medium",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == uploaded["document_id"]
    assert body["summary"].strip()
    assert "metrics" in body
    assert "rouge_1" in body["metrics"]
    assert "bleu" in body["metrics"]


def test_evaluate_unknown_document_is_404(client):
    response = client.post(
        "/api/evaluate",
        json={"document_id": "does-not-exist", "reference": "Ref text"},
    )
    assert response.status_code == 404
