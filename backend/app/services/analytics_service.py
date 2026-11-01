"""
Analytics service: readability scoring, keyphrase extraction,
faithfulness/hallucination detection, and source sentence attribution.

Designed to give deep academic credibility, transparency, and explainability
to generated summaries.
"""

import logging
import math
import re
from typing import Any

import numpy as np

from app.config import settings
from app.services.chunking_service import split_sentences

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Readability Analytics (Flesch Reading Ease & Flesch-Kincaid Grade Level)
# ---------------------------------------------------------------------------

def _count_syllables_in_word(word: str) -> int:
    """Estimate syllable count in a single English word using phonetic regex heuristics."""
    word = word.lower().strip()
    if not word:
        return 0
    if len(word) <= 3:
        return 1

    # Remove non-alphabetic characters
    word = re.sub(r"[^a-z]", "", word)
    if not word:
        return 0

    # Common suffix handling
    if word.endswith("e") and not word.endswith("le"):
        word = word[:-1]

    # Count vowel groups
    vowels = "aeiouy"
    count = 0
    prev_is_vowel = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_is_vowel:
            count += 1
        prev_is_vowel = is_vowel

    return max(1, count)


def compute_readability(text: str) -> dict[str, Any]:
    """Calculate Flesch Reading Ease, Flesch-Kincaid Grade Level, and Reading Time.

    Formulas:
      Flesch Reading Ease = 206.835 - (1.015 * ASL) - (84.6 * ASW)
        where ASL = Average Sentence Length (words / sentences)
              ASW = Average Syllables per Word (syllables / words)
      Flesch-Kincaid Grade = (0.39 * ASL) + (11.8 * ASW) - 15.59
    """
    clean_text = text.strip()
    if not clean_text:
        return {
            "flesch_reading_ease": 0.0,
            "reading_level": "N/A",
            "grade_level": 0.0,
            "reading_time_seconds": 0,
            "word_count": 0,
            "sentence_count": 0,
        }

    sentences = split_sentences(clean_text)
    num_sentences = max(1, len(sentences))

    # Tokenize words (ignoring standalone punctuation)
    words = [w for w in re.findall(r"\b[A-Za-z0-9'-]+\b", clean_text) if any(c.isalnum() for c in w)]
    num_words = max(1, len(words))

    total_syllables = sum(_count_syllables_in_word(w) for w in words)

    asl = num_words / num_sentences
    asw = total_syllables / num_words

    # Compute Flesch Reading Ease (bounded [0, 100])
    fre = 206.835 - (1.015 * asl) - (84.6 * asw)
    fre = round(max(0.0, min(100.0, fre)), 1)

    # Compute Grade Level (bounded >= 0)
    fk_grade = round(max(0.0, (0.39 * asl) + (11.8 * asw) - 15.59), 1)

    # Human-readable interpretation
    if fre >= 80:
        level = "Easy (School level)"
    elif fre >= 60:
        level = "Standard (Plain English)"
    elif fre >= 50:
        level = "Fairly Difficult (High School)"
    elif fre >= 30:
        level = "Difficult (College level)"
    else:
        level = "Very Difficult (Academic / Technical)"

    # Reading speed: average adult reads ~220 words per minute (~3.67 words/sec)
    reading_seconds = max(1, int(math.ceil(num_words / (220 / 60))))

    return {
        "flesch_reading_ease": fre,
        "reading_level": level,
        "grade_level": fk_grade,
        "reading_time_seconds": reading_seconds,
        "word_count": num_words,
        "sentence_count": num_sentences,
    }


def compare_readability(original_text: str, summary_text: str) -> dict[str, Any]:
    """Compute comparative readability and time savings between source and summary."""
    orig = compute_readability(original_text)
    summ = compute_readability(summary_text)

    orig_time = orig["reading_time_seconds"]
    summ_time = summ["reading_time_seconds"]
    time_saved_sec = max(0, orig_time - summ_time)
    time_saved_pct = round((time_saved_sec / orig_time * 100.0), 1) if orig_time > 0 else 0.0

    ease_improvement = round(summ["flesch_reading_ease"] - orig["flesch_reading_ease"], 1)

    return {
        "original": orig,
        "summary": summ,
        "time_saved_seconds": time_saved_sec,
        "time_saved_percent": time_saved_pct,
        "ease_improvement": ease_improvement,
    }


# ---------------------------------------------------------------------------
# Keyphrase / Semantic Topic Extraction
# ---------------------------------------------------------------------------

COMMON_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than",
    "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't",
    "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's",
    "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom",
    "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll",
    "you're", "you've", "your", "yours", "yourself", "yourselves", "also", "one", "two",
    "first", "using", "used", "may", "show", "shows", "shown", "table", "figure"
}


def extract_keyphrases(text: str, top_k: int = 6) -> list[str]:
    """Extract prominent keyphrases and topical terms from text.

    Uses candidate n-gram filtering with frequency and length heuristics.
    """
    clean = text.lower()
    # Extract candidate unigrams and bigrams
    words = [w for w in re.findall(r"\b[a-z]{3,}\b", clean) if w not in COMMON_STOPWORDS]
    if not words:
        return []

    counts: dict[str, float] = {}

    # Score unigrams
    for w in words:
        counts[w] = counts.get(w, 0.0) + 1.0

    # Score meaningful bigrams
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i + 1]
        bigram = f"{w1} {w2}"
        counts[bigram] = counts.get(bigram, 0.0) + 2.5

    # Filter out sub-phrases with lower relative counts
    sorted_phrases = sorted(counts.items(), key=lambda x: (x[1], len(x[0])), reverse=True)
    results: list[str] = []
    for phrase, _ in sorted_phrases:
        # Don't add duplicate or contained terms
        if not any(phrase in r or r in phrase for r in results):
            results.append(phrase.title())
        if len(results) >= top_k:
            break

    return results


# ---------------------------------------------------------------------------
# Faithfulness / Hallucination Detection & Source Sentence Attribution
# ---------------------------------------------------------------------------

def check_faithfulness_and_attribution(
    original_text: str, summary_text: str
) -> dict[str, Any]:
    """Check how well the summary is grounded in the original source text.

    Uses Sentence-Transformers embeddings (MiniLM) to evaluate the maximum semantic
    alignment of each summary sentence against all source sentences.

    Returns:
      - overall_confidence: 0-100% confidence score
      - hallucination_risk: 'low' | 'medium' | 'high'
      - grounded_count: number of firmly grounded sentences
      - total_summary_sentences: count of summary sentences
      - sentence_attributions: list of details mapping each summary sentence to its
        best-matching source sentence with similarity score and grounded flag.
    """
    summary_sentences = split_sentences(summary_text)
    source_sentences = split_sentences(original_text)

    if not summary_sentences or not source_sentences:
        return {
            "overall_confidence": 100.0,
            "hallucination_risk": "low",
            "grounded_count": 0,
            "total_summary_sentences": 0,
            "sentence_attributions": [],
        }

    # Use the cached MiniLM model from extractive_service
    from app.services.extractive_service import _model

    embedder = _model()

    # Encode both sets with normalisation for instant cosine dot-product
    source_embeddings = embedder.encode(source_sentences, normalize_embeddings=True)
    summary_embeddings = embedder.encode(summary_sentences, normalize_embeddings=True)

    # Matrix multiplication yields cosine similarity shape: (num_summary, num_source)
    similarity_matrix = summary_embeddings @ source_embeddings.T

    attributions: list[dict[str, Any]] = []
    grounded_count = 0
    total_score = 0.0

    for i, sum_sent in enumerate(summary_sentences):
        row = similarity_matrix[i]
        best_source_idx = int(np.argmax(row))
        max_sim = float(row[best_source_idx])

        # A score >= 0.52 indicates strong semantic preservation / entailment
        is_grounded = max_sim >= 0.52
        if is_grounded:
            grounded_count += 1

        total_score += max_sim

        attributions.append({
            "summary_sentence": sum_sent,
            "source_sentence_index": best_source_idx,
            "source_sentence": source_sentences[best_source_idx],
            "similarity": round(max_sim, 3),
            "is_grounded": is_grounded,
        })

    avg_similarity = total_score / len(summary_sentences)
    confidence_pct = round(max(0.0, min(100.0, avg_similarity * 100.0)), 1)

    grounded_ratio = grounded_count / len(summary_sentences)
    if grounded_ratio >= 0.8:
        risk = "low"
    elif grounded_ratio >= 0.5:
        risk = "medium"
    else:
        risk = "high"

    return {
        "overall_confidence": confidence_pct,
        "hallucination_risk": risk,
        "grounded_count": grounded_count,
        "total_summary_sentences": len(summary_sentences),
        "sentence_attributions": attributions,
    }

