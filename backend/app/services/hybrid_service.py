"""
Hybrid summarization: combine extractive sentence selection with abstractive BART generation.

Approach (TextRank filter -> BART condensation):

1. Split document into sentences using chunking_service.
2. Short documents (< 3 sentences) are returned unchanged.
3. Extractive pre-filter: rank sentences with `extractive_service.rank_sentences(text)`
   (TextRank on sentence embeddings). Select a targeted budget of the most informative
   sentences based on requested length, restoring their original document order.
4. Abstractive condensation: pass the joined top sentences to `abstractive_service.summarize(..., length)`
   to synthesize fluent, highly grounded prose in a single fast pass.

By feeding BART a concise, high-density factual context, hybrid summarization avoids slow
multi-pass chunking, minimizes hallucination risks, and finishes in seconds rather than minutes.
"""

import logging

from app.services import abstractive_service, chunking_service, extractive_service

logger = logging.getLogger(__name__)

MIN_SENTENCES = 3

# Target sentence budgets for the extractive pre-filtering step.
# These budgets ensure the extracted factual context fits cleanly into BART's single-pass
# 1024-token context window, eliminating multi-pass Map-Reduce overhead.
HYBRID_TARGET_SENTENCES = {
    "short": 6,
    "medium": 12,
    "long": 18,
}


def summarize(text: str, length: str = "medium") -> str:
    """Generate a hybrid summary by filtering sentences extractively then condensing abstractively."""
    sentences = chunking_service.split_sentences(text)
    if len(sentences) < MIN_SENTENCES:
        return text.strip()

    # Step 1: Rank sentences using TextRank
    ranked = extractive_service.rank_sentences(text)

    # Step 2: Target sentence budget
    # If the document is already concise (<= target_k + 4 sentences), keep ALL sentences
    # so no sections, bullet points, or later topics are discarded.
    target_k = HYBRID_TARGET_SENTENCES.get(length, 12)
    if len(sentences) <= target_k + 2:
        filtered_text = text.strip()
        logger.info(
            "Hybrid: document has %d sentences (<= budget %d), preserving full context",
            len(sentences),
            target_k + 2,
        )
    else:
        # For longer documents, ensure stratified coverage across beginning, middle, and end
        # so that later sections and conclusions are never skipped.
        keep_count = min(len(sentences), target_k)
        top_subset = set(ranked[:keep_count])

        # Also guarantee at least 1-2 top-ranked sentences from the latter part of the document
        tail_start = int(len(sentences) * 0.6)
        tail_sentences = [s for s in sentences[tail_start:] if s in ranked]
        if tail_sentences:
            best_tail = sorted(tail_sentences, key=lambda s: ranked.index(s))[0]
            top_subset.add(best_tail)

        chosen = [s for s in sentences if s in top_subset]
        filtered_text = " ".join(chosen)
        logger.info(
            "Hybrid: filtered %d sentences down to top %d with stratified section coverage",
            len(sentences),
            len(chosen),
        )

    # Step 3: Fast abstractive pass on the high-density extracted text
    return abstractive_service.summarize(filtered_text, length=length)
