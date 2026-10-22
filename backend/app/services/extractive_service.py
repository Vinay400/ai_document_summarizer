"""
Extractive summarization: pick the most representative sentences.

Approach (embeddings + TextRank):

1. Split the document into sentences.
2. Embed each one with all-MiniLM-L6-v2.
3. Build a graph whose nodes are sentences and whose edge weights are the
   cosine similarity between them.
4. Run PageRank over it and keep the highest-scoring sentences.

A sentence therefore scores highly when it is *similar to many others* - when it
is representative of the document - rather than when it is long or contains
frequent words. Nothing is rewritten: every returned sentence is quoted verbatim
from the source, which is what makes extractive summarization unable to
hallucinate.
"""

import logging
from functools import lru_cache

import networkx as nx
import numpy as np

from app.config import settings
from app.services.chunking_service import split_sentences

logger = logging.getLogger(__name__)

# Fraction of the document's sentences to keep for each requested length.
LENGTH_RATIOS = {"short": 0.15, "medium": 0.3, "long": 0.5}

# Below this many sentences there is nothing worth compressing.
MIN_SENTENCES = 3


@lru_cache(maxsize=1)
def _model():
    """The embedding model, loaded once per process and cached afterwards.

    Imported here rather than at module level so that starting the API does not
    pull in torch: only the first /api/summarize call pays for it.
    """
    from sentence_transformers import SentenceTransformer

    logger.info("Loading extractive model %s", settings.EXTRACTIVE_MODEL)
    return SentenceTransformer(settings.EXTRACTIVE_MODEL)


def rank_sentences(text: str) -> list[str]:
    """Rank sentences by TextRank score using MiniLM embeddings, returning sentences best-first."""
    sentences = split_sentences(text)
    if not sentences:
        return []
    if len(sentences) == 1:
        return sentences

    embeddings = _model().encode(sentences, normalize_embeddings=True)

    # Normalised embeddings make the dot product the cosine similarity.
    # Similarities are clipped at zero because PageRank needs non-negative
    # weights, and the diagonal is cleared so a sentence cannot reinforce itself.
    similarity = np.clip(embeddings @ embeddings.T, 0.0, None)
    np.fill_diagonal(similarity, 0.0)

    scores = nx.pagerank(nx.from_numpy_array(similarity))
    ranked_indices = sorted(scores, key=scores.get, reverse=True)
    return [sentences[i] for i in ranked_indices]


def summarize(text: str, length: str = "medium") -> str:
    """Return the most representative sentences, in their original order.

    Short documents are returned unchanged - compressing three sentences into
    one loses more than it gains.
    """
    sentences = split_sentences(text)
    if len(sentences) < MIN_SENTENCES:
        return text.strip()

    ranked = rank_sentences(text)
    keep = max(1, round(len(sentences) * LENGTH_RATIOS.get(length, 0.3)))

    top_k = ranked[:keep]
    top_k_counts = {}
    for s in top_k:
        top_k_counts[s] = top_k_counts.get(s, 0) + 1

    chosen = []
    for s in sentences:
        if top_k_counts.get(s, 0) > 0:
            chosen.append(s)
            top_k_counts[s] -= 1

    summary = " ".join(chosen)
    logger.info("Extractive: kept %d of %d sentence(s)", keep, len(sentences))
    return summary
