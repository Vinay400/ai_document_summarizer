"""
Unit tests for analytics_service (readability, keyphrase extraction, and faithfulness).
"""

from app.services import analytics_service


def test_compute_readability_metrics():
    text = (
        "Artificial intelligence and natural language processing allow computers "
        "to analyze, understand, and generate human language in a useful way."
    )
    result = analytics_service.compute_readability(text)
    assert "flesch_reading_ease" in result
    assert "grade_level" in result
    assert "reading_time_seconds" in result
    assert result["word_count"] > 0
    assert result["sentence_count"] >= 1
    assert 0.0 <= result["flesch_reading_ease"] <= 100.0


def test_compute_readability_empty():
    result = analytics_service.compute_readability("")
    assert result["word_count"] == 0
    assert result["flesch_reading_ease"] == 0.0


def test_compare_readability():
    original = (
        "The implementation of sequence to sequence neural network architectures "
        "provides significant algorithmic advantages for deep textual summarization tasks."
    )
    summary = "Neural networks summarize text well."
    comparison = analytics_service.compare_readability(original, summary)
    assert "time_saved_percent" in comparison
    assert "time_saved_seconds" in comparison
    assert "ease_improvement" in comparison
    assert comparison["time_saved_percent"] >= 0.0


def test_extract_keyphrases():
    text = (
        "Deep learning and transformer architectures have revolutionized text summarization. "
        "Natural language processing systems utilize neural networks to process long documents."
    )
    keyphrases = analytics_service.extract_keyphrases(text, top_k=4)
    assert isinstance(keyphrases, list)
    assert len(keyphrases) > 0
    assert all(isinstance(k, str) for k in keyphrases)


def test_faithfulness_stubbed(monkeypatch):
    """Test faithfulness scoring logic with mock embeddings to keep tests fast."""
    import numpy as np

    class MockEmbedder:
        def encode(self, sentences, normalize_embeddings=True):
            # Return identity-like normalized vectors for testing
            n = len(sentences)
            vecs = np.ones((n, 8), dtype=float)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            return vecs / norms

    monkeypatch.setattr("app.services.extractive_service._model", lambda: MockEmbedder())

    orig = "Sentence one about machine learning. Sentence two about deep neural networks."
    summ = "Sentence one about machine learning."
    faith = analytics_service.check_faithfulness_and_attribution(orig, summ)

    assert "overall_confidence" in faith
    assert "hallucination_risk" in faith
    assert faith["hallucination_risk"] in ("low", "medium", "high")
    assert len(faith["sentence_attributions"]) == 1
    assert faith["sentence_attributions"][0]["is_grounded"] is True

