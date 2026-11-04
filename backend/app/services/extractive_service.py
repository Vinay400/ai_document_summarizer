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
import re
from functools import lru_cache

import networkx as nx
import numpy as np

from app.config import settings
from app.services.chunking_service import split_sentences

logger = logging.getLogger(__name__)

# Target sentence budgets and scaling ratios per requested length.
# Rather than keeping an unbounded percentage that swings wildly between 2 and 40 sentences,
# we use calibrated target counts with min/max bounds to ensure short, medium, and long
# summaries are distinct, meaningful, and well-budgeted.
LENGTH_SETTINGS = {
    "short": {"target": 3, "min": 2, "max": 4, "ratio": 0.18},
    "medium": {"target": 6, "min": 4, "max": 8, "ratio": 0.35},
    "long": {"target": 12, "min": 6, "max": 14, "ratio": 0.55},
}

# Below this many sentences there is nothing worth compressing.
MIN_SENTENCES = 3


def is_candidate_sentence(s: str) -> bool:
    """Filter out unparsed tabular dumps, citations, and placeholders.
    
    A clean narrative sentence:
    - Has between 5 and 75 words.
    - Is not a raw citation header like '[1]', 'References', 'Table 1.1'.
    - Is not an image placeholder like '[ INSERT PHOTOGRAPH ... ]'.
    - Does not contain multiple semi-colons or pipes typical of unparsed tables.
    """
    words = s.split()
    if len(words) < 5 or len(words) > 75:
        return False
    if re.search(r"\[\s*INSERT\b", s, re.IGNORECASE):
        return False
    if re.match(r"^(\[\d+\]|References?\b|Table\s+\d+|Figure\s+\d+|http[s]?://)", s, re.IGNORECASE):
        return False
    if s.count(";") > 4 or s.count("|") > 2:
        return False
    return True


@lru_cache(maxsize=1)
def _model():
    """The embedding model, loaded once per process and cached afterwards.

    Imported here rather than at module level so that starting the API does not
    pull in torch: only the first /api/summarize call pays for it.
    """
    from sentence_transformers import SentenceTransformer

    logger.info("Loading extractive model %s", settings.EXTRACTIVE_MODEL)
    try:
        return SentenceTransformer(settings.EXTRACTIVE_MODEL, local_files_only=True)
    except Exception:
        return SentenceTransformer(settings.EXTRACTIVE_MODEL)


def rank_sentences(text: str) -> list[str]:
    """Rank sentences by TextRank score using MiniLM embeddings, returning sentences best-first."""
    sentences = split_sentences(text)
    if not sentences:
        return []
    if len(sentences) == 1:
        return sentences

    # Prioritize clean narrative sentences for ranking graph construction
    candidates = [s for s in sentences if is_candidate_sentence(s)]
    # Fallback to all sentences if document has few sentences or is heavily formatted
    working_sentences = candidates if len(candidates) >= MIN_SENTENCES else sentences

    embeddings = _model().encode(working_sentences, normalize_embeddings=True)

    # Normalised embeddings make the dot product the cosine similarity.
    # Similarities are clipped at zero because PageRank needs non-negative
    # weights, and the diagonal is cleared so a sentence cannot reinforce itself.
    similarity = np.clip(embeddings @ embeddings.T, 0.0, None)
    np.fill_diagonal(similarity, 0.0)

    scores = nx.pagerank(nx.from_numpy_array(similarity))
    ranked_indices = sorted(scores, key=scores.get, reverse=True)
    return [working_sentences[i] for i in ranked_indices]


def summarize(text: str, length: str = "medium") -> str:
    """Return the most representative sentences, in their original order.

    Short documents are returned unchanged - compressing three sentences into
    one loses more than it gains.
    """
    sentences = split_sentences(text)
    if len(sentences) < MIN_SENTENCES:
        return text.strip()

    cfg = LENGTH_SETTINGS.get(length, LENGTH_SETTINGS["medium"])
    ranked = rank_sentences(text)
    if not ranked:
        return text.strip()

    # Calculate calibrated sentence budget:
    # 1. Scale with document length using ratio
    # 2. Bound between min and max bounds for the requested length
    # 3. Ensure keep does not exceed available ranked sentences
    scaled_count = round(len(ranked) * cfg["ratio"])
    keep = min(len(ranked), max(cfg["min"], min(cfg["max"], scaled_count)))

    # On shorter texts, ensure strict hierarchy: short < medium < long
    if length == "short":
        keep = min(keep, max(1, len(ranked) - 2))
    elif length == "long":
        keep = min(len(ranked), max(keep, min(len(ranked), cfg["min"] + 2)))

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
    logger.info("Extractive: kept %d of %d sentence(s) for length '%s'", len(chosen), len(sentences), length)
    return summary
