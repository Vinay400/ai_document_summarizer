"""
Abstractive summarization: generate new sentences that condense the source text.

Approach (BART + Map-Reduce):

1. Short documents (< 40 words) are returned unchanged.
2. Tokenize text using facebook/bart-large-cnn tokenizer.
3. If the input fits in a single chunk (<= 900 tokens), summarize directly.
4. Otherwise, use map-reduce:
   - Map phase: split document into overlapping sentence-aligned chunks using
     chunking_service. Summarize each chunk independently.
   - Reduce phase: concatenate partial summaries. If the result still exceeds 900
     tokens, chunk and summarize ONCE more (reduce) without looping indefinitely.

Abstractive models rewrite and synthesize concepts into fluent prose. However,
unlike extractive methods, they carry a slight risk of hallucination, which is why
a hybrid pipeline (Phase 7) is also provided.
"""

import logging
from functools import lru_cache

from app.config import settings
from app.services import chunking_service

logger = logging.getLogger(__name__)

# Target generation parameters per requested length.
LENGTH_SETTINGS = {
    "short": {"max_new_tokens": 120, "min_new_tokens": 40},
    "medium": {"max_new_tokens": 220, "min_new_tokens": 80},
    "long": {"max_new_tokens": 400, "min_new_tokens": 140},
}

MIN_WORDS = 40
MAX_SINGLE_PASS_TOKENS = 900
BART_MAX_INPUT_TOKENS = 1024


@lru_cache(maxsize=1)
def _model():
    """Load the BART tokenizer and sequence-to-sequence model once per process.

    Imported inside this function so starting the application or running non-abstractive
    tests does not trigger heavy PyTorch / transformers imports or model loading.
    """
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    logger.info("Loading abstractive model %s on device %s", settings.ABSTRACTIVE_MODEL, settings.ABSTRACTIVE_DEVICE)
    tokenizer = AutoTokenizer.from_pretrained(settings.ABSTRACTIVE_MODEL)
    model = AutoModelForSeq2SeqLM.from_pretrained(settings.ABSTRACTIVE_MODEL)
    model.to(settings.ABSTRACTIVE_DEVICE)
    model.eval()
    return tokenizer, model


def _generate_chunk_summary(text: str, length: str) -> str:
    """Summarize a single chunk of text that fits within the token limit."""
    tokenizer, model = _model()
    import torch

    params = LENGTH_SETTINGS.get(length, LENGTH_SETTINGS["medium"])
    inputs = tokenizer(
        text,
        truncation=True,
        max_length=BART_MAX_INPUT_TOKENS,
        return_tensors="pt",
    ).to(settings.ABSTRACTIVE_DEVICE)

    input_token_count = inputs["input_ids"].shape[1]
    min_tokens = min(params["min_new_tokens"], max(10, input_token_count - 5))
    max_tokens = max(min_tokens + 10, params["max_new_tokens"])

    with torch.no_grad():
        summary_ids = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            min_new_tokens=min_tokens,
            num_beams=4,
            early_stopping=True,
        )

    decoded = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return decoded.strip()


def summarize(text: str, length: str = "medium") -> str:
    """Generate an abstractive summary using BART with map-reduce chunking if needed."""
    stripped = text.strip()
    words = stripped.split()
    if len(words) < MIN_WORDS:
        return stripped

    tokenizer, _ = _model()
    token_ids = tokenizer.encode(stripped, truncation=False)

    # Fits in one chunk directly
    if len(token_ids) <= MAX_SINGLE_PASS_TOKENS:
        return _generate_chunk_summary(stripped, length)

    # Map step: chunk text and summarize each chunk
    chunks = chunking_service.chunk_text(stripped)
    if not chunks:
        return stripped

    logger.info("Abstractive map phase: summarizing %d chunks", len(chunks))
    partial_summaries = [_generate_chunk_summary(c.text, length) for c in chunks]
    joined_summary = " ".join(partial_summaries).strip()

    # Reduce step: check if joined partial summaries exceed token limit
    joined_tokens = tokenizer.encode(joined_summary, truncation=False)
    if len(joined_tokens) > MAX_SINGLE_PASS_TOKENS:
        logger.info("Abstractive reduce phase: joined summary (%d tokens) exceeds limit, reducing", len(joined_tokens))
        reduce_chunks = chunking_service.chunk_text(joined_summary)
        if reduce_chunks:
            reduced_summaries = [_generate_chunk_summary(rc.text, length) for rc in reduce_chunks]
            return " ".join(reduced_summaries).strip()

    return joined_summary
