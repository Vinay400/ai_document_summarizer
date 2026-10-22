"""
Hybrid summarization: combine extractive sentence selection with abstractive BART generation.

Approach (TextRank filter -> BART condensation):

1. Split document into sentences using chunking_service.
2. Short documents (< 3 sentences) are returned unchanged.
3. Extractive pre-filter: rank sentences with `extractive_service.rank_sentences(text)`
   (TextRank on sentence embeddings). Select the top ~50% of sentences by rank and
   restore their original document order.
4. Abstractive condensation: pass the joined top sentences to `abstractive_service.summarize(..., length)`
   to synthesize fluent prose.

By feeding BART only high-importance sentences, hybrid summarization reduces hallucination
risks while maintaining abstractive fluency and conciseness.
"""

import logging

from app.services import abstractive_service, chunking_service, extractive_service

logger = logging.getLogger(__name__)

MIN_SENTENCES = 3


def summarize(text: str, length: str = "medium") -> str:
    """Generate a hybrid summary by filtering sentences extractively then condensing abstractively."""
    sentences = chunking_service.split_sentences(text)
    if len(sentences) < MIN_SENTENCES:
        return text.strip()

    # Step 1: Rank sentences using TextRank
    ranked = extractive_service.rank_sentences(text)

    # Step 2: Select top ~50% of sentences by rank
    keep_count = max(1, round(len(sentences) * 0.5))
    top_half = ranked[:keep_count]

    top_counts = {}
    for s in top_half:
        top_counts[s] = top_counts.get(s, 0) + 1

    chosen = []
    for s in sentences:
        if top_counts.get(s, 0) > 0:
            chosen.append(s)
            top_counts[s] -= 1

    filtered_text = " ".join(chosen)
    logger.info(
        "Hybrid: filtered %d sentences down to top %d before abstractive pass",
        len(sentences),
        len(chosen),
    )

    # Step 3: Abstractive pass on the extractively pre-filtered text
    return abstractive_service.summarize(filtered_text, length=length)
