"""
Unit tests for qa_service (RAG Question-Answering).
"""

from app.services import qa_service


def test_answer_document_question_empty():
    res = qa_service.answer_document_question("", "")
    assert res["confidence"] == 0.0
    assert "Please provide" in res["answer"]


def test_answer_document_question_mocked(monkeypatch):
    import numpy as np

    class MockEmbedder:
        def encode(self, texts, normalize_embeddings=True):
            n = len(texts)
            vecs = np.random.randn(n, 8)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            return vecs / norms

    monkeypatch.setattr("app.services.extractive_service._model", lambda: MockEmbedder())

    doc = (
        "The project uses FastAPI on the backend and React on the frontend. "
        "PostgreSQL and SQLite provide persistent database storage for document history. "
        "Evaluation is measured using ROUGE and BLEU scores."
    )
    question = "What database is used?"

    res = qa_service.answer_document_question(doc, question, top_k=2)
    assert "answer" in res
    assert "sources" in res
    assert "confidence" in res
    assert res["question"] == question

