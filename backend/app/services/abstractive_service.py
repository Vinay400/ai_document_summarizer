"""
Abstractive summarization: generate new sentences that condense the source text.

Approach (BART + Fast Map-Reduce):

1. Short documents (< 40 words) are returned unchanged.
2. Tokenize text using the seq2seq tokenizer.
3. If the input fits in a single chunk (<= 900 tokens), summarize directly using
   fast 2-beam inference with no-repeat ngram penalties.
4. Otherwise, use optimized Map-Reduce:
   - Map phase: split document into overlapping sentence-aligned chunks using
     chunking_service. Summarize each chunk with concise token budgets and fast beam search.
   - Reduce phase: concatenate partial summaries and perform a single cohesive condensation
     pass if needed, avoiding redundant re-chunking loops.

Performance optimizations for CPU:
- Uses `torch.inference_mode()` instead of `torch.no_grad()` to strip autograd overhead.
- Optimized beam search: `num_beams=2` (cuts generation latency in half compared to 4 beams).
- `no_repeat_ngram_size=3` and `early_stopping=True` to stop decoding as soon as thoughts complete.
- Lean Map-phase budgets: intermediate chunks generate concise partial summaries,
  preventing huge intermediate texts and eliminating redundant reduce cycles.
"""

import logging
from functools import lru_cache

from app.config import settings
from app.services import chunking_service

logger = logging.getLogger(__name__)

# Target generation parameters per requested length for final summary.
LENGTH_SETTINGS = {
    "short": {"max_new_tokens": 100, "min_new_tokens": 30},
    "medium": {"max_new_tokens": 180, "min_new_tokens": 60},
    "long": {"max_new_tokens": 300, "min_new_tokens": 100},
}

# Intermediate map-phase parameters (concise partial summaries for speed)
MAP_CHUNK_SETTINGS = {
    "short": {"max_new_tokens": 60, "min_new_tokens": 20},
    "medium": {"max_new_tokens": 90, "min_new_tokens": 30},
    "long": {"max_new_tokens": 130, "min_new_tokens": 40},
}

MIN_WORDS = 40
MAX_SINGLE_PASS_TOKENS = 900
BART_MAX_INPUT_TOKENS = 1024


@lru_cache(maxsize=1)
def _model():
    """Load the seq2seq tokenizer and model once per process."""
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    import torch

    # Optimize CPU intra-op thread count if running on CPU
    if settings.ABSTRACTIVE_DEVICE == "cpu":
        try:
            torch.set_num_threads(max(1, torch.get_num_threads()))
        except Exception:
            pass

    logger.info("Loading abstractive model %s on device %s", settings.ABSTRACTIVE_MODEL, settings.ABSTRACTIVE_DEVICE)
    tokenizer = AutoTokenizer.from_pretrained(settings.ABSTRACTIVE_MODEL)
    model = AutoModelForSeq2SeqLM.from_pretrained(settings.ABSTRACTIVE_MODEL)
    model.to(settings.ABSTRACTIVE_DEVICE)
    model.eval()
    return tokenizer, model


def _generate_chunk_summary(text: str, length: str, is_intermediate: bool = False) -> str:
    """Summarize a single chunk of text with optimized beam search."""
    tokenizer, model = _model()
    import torch

    settings_dict = MAP_CHUNK_SETTINGS if is_intermediate else LENGTH_SETTINGS
    params = settings_dict.get(length, settings_dict["medium"])

    inputs = tokenizer(
        text,
        truncation=True,
        max_length=BART_MAX_INPUT_TOKENS,
        return_tensors="pt",
    ).to(settings.ABSTRACTIVE_DEVICE)

    input_token_count = inputs["input_ids"].shape[1]
    min_tokens = min(params["min_new_tokens"], max(10, input_token_count - 5))
    max_tokens = max(min_tokens + 10, params["max_new_tokens"])

    # Fast 2-beam decoding for CPU efficiency
    num_beams = 2

    with torch.inference_mode():
        summary_ids = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            min_new_tokens=min_tokens,
            num_beams=num_beams,
            no_repeat_ngram_size=3,
            early_stopping=True,
            forced_bos_token_id=0,
        )

    decoded = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return decoded.strip()


def summarize(text: str, length: str = "medium") -> str:
    """Generate an abstractive summary using BART with fast map-reduce chunking if needed."""
    stripped = text.strip()
    words = stripped.split()
    if len(words) < MIN_WORDS:
        return stripped

    tokenizer, _ = _model()
    token_ids = tokenizer.encode(stripped, truncation=False)

    # Fits in one chunk directly: single fast pass
    if len(token_ids) <= MAX_SINGLE_PASS_TOKENS:
        return _generate_chunk_summary(stripped, length, is_intermediate=False)

    # Map step: chunk text and summarize each chunk with intermediate settings
    chunks = chunking_service.chunk_text(stripped)
    if not chunks:
        return stripped

    logger.info("Abstractive map phase: summarizing %d chunks with fast intermediate budgets", len(chunks))
    partial_summaries = [_generate_chunk_summary(c.text, length, is_intermediate=True) for c in chunks]
    joined_summary = " ".join(partial_summaries).strip()

    # Reduce step: check if joined partial summaries exceed token limit
    joined_tokens = tokenizer.encode(joined_summary, truncation=False)
    if len(joined_tokens) > MAX_SINGLE_PASS_TOKENS:
        logger.info("Abstractive reduce phase: joined summary (%d tokens) exceeds limit, reducing", len(joined_tokens))
        # If still very long, chunk once and condense
        reduce_chunks = chunking_service.chunk_text(joined_summary)
        if reduce_chunks:
            reduced = [_generate_chunk_summary(rc.text, length, is_intermediate=True) for rc in reduce_chunks]
            joined_summary = " ".join(reduced).strip()

    # Final condensation pass to unify partial summaries into one fluent summary
    if len(chunks) > 1 and len(joined_summary.split()) > 70:
        logger.info("Abstractive reduce phase: condensing %d partial summaries into final cohesive summary", len(chunks))
        return _generate_chunk_summary(joined_summary, length, is_intermediate=False)

    return joined_summary
