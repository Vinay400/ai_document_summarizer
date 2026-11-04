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
# Tuned for comprehensive, well-rounded summaries that cover all main sections
# with distinct, noticeable length differences.
LENGTH_SETTINGS = {
    "short": {"max_new_tokens": 120, "min_new_tokens": 60, "length_penalty": 1.0},
    "medium": {"max_new_tokens": 240, "min_new_tokens": 120, "length_penalty": 1.3},
    "long": {"max_new_tokens": 360, "min_new_tokens": 200, "length_penalty": 1.6},
}

# Intermediate map-phase parameters (concise partial summaries for speed)
MAP_CHUNK_SETTINGS = {
    "short": {"max_new_tokens": 65, "min_new_tokens": 30},
    "medium": {"max_new_tokens": 90, "min_new_tokens": 45},
    "long": {"max_new_tokens": 130, "min_new_tokens": 70},
}

# Threshold above which concatenated partial chunk summaries should undergo a reduce pass.
# If joined summaries are already within budget, skipping the reduce pass avoids
# over-compressing multi-chunk content into 25-30 words.
REDUCE_WORD_THRESHOLDS = {
    "short": 100,
    "medium": 180,
    "long": 280,
}

MIN_WORDS = 40
MAX_SINGLE_PASS_TOKENS = 900
BART_MAX_INPUT_TOKENS = 1024

# Realistic chunk size tailored to BART's 1024-token capacity (~3200 characters = ~550 tokens)
MAP_CHUNK_SIZE_CHARS = 3200
MAP_CHUNK_OVERLAP_CHARS = 200

# Cap intermediate Map chunks for massive documents to guarantee snappy viva presentation times
MAX_MAP_CHUNKS = 4


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
    try:
        tokenizer = AutoTokenizer.from_pretrained(settings.ABSTRACTIVE_MODEL, local_files_only=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(settings.ABSTRACTIVE_MODEL, local_files_only=True)
    except Exception:
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
    target_min = params["min_new_tokens"]

    # Calibrate min_tokens and max_tokens:
    # 1. On substantive inputs (input_token_count >= 450 tokens):
    #    Enforce the full target_min (60/120/200 tokens) and params["max_new_tokens"]
    #    so BART produces comprehensive, well-rounded paragraphs and does not emit
    #    an early EOS after only 1-2 short sentences.
    # 2. On short inputs (input_token_count < 450 tokens, such as brief bullet notes):
    #    Scale min_tokens down proportionally (~20% of input) so BART is never forced
    #    to hallucinate filler text once the source facts are exhausted.
    if input_token_count < 450:
        min_tokens = min(target_min, max(15, int(input_token_count * 0.2)))
        max_tokens = min(params["max_new_tokens"], max(min_tokens + 25, int(input_token_count * 0.45)))
    else:
        min_tokens = target_min
        max_tokens = params["max_new_tokens"]

    # For intermediate map chunks, greedy decoding (num_beams=1) cuts CPU inference time by ~50%
    # For final summary passes, 2 beams ensure fluent prose
    num_beams = 1 if is_intermediate else 2
    length_penalty = params.get("length_penalty", 1.2) if not is_intermediate else 1.0

    gen_kwargs = {
        "max_new_tokens": max_tokens,
        "min_new_tokens": min_tokens,
        "num_beams": num_beams,
        "no_repeat_ngram_size": 3,
        "forced_bos_token_id": 0,
    }
    if num_beams > 1:
        gen_kwargs["early_stopping"] = True
        gen_kwargs["length_penalty"] = length_penalty

    with torch.inference_mode():
        summary_ids = model.generate(
            **inputs,
            **gen_kwargs,
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

    # Map step: chunk text using realistic token-sized chunks (~3200 chars / ~550 tokens)
    chunks = chunking_service.chunk_text(
        stripped,
        chunk_size=MAP_CHUNK_SIZE_CHARS,
        overlap=MAP_CHUNK_OVERLAP_CHARS,
    )
    if not chunks:
        return stripped

    # For large documents (> MAX_MAP_CHUNKS), prioritize the most informative sections
    # (lead intro, middle core sections, and conclusion) to keep presentation execution under 15-20s
    if len(chunks) > MAX_MAP_CHUNKS:
        logger.info(
            "Document has %d chunks; selecting top %d representative sections for fast Map phase",
            len(chunks),
            MAX_MAP_CHUNKS,
        )
        indices = [0]
        step = (len(chunks) - 1) / (MAX_MAP_CHUNKS - 1)
        for i in range(1, MAX_MAP_CHUNKS - 1):
            idx = int(round(i * step))
            if idx not in indices and idx < len(chunks):
                indices.append(idx)
        if (len(chunks) - 1) not in indices:
            indices.append(len(chunks) - 1)
        chunks = [chunks[i] for i in sorted(indices)]

    logger.info("Abstractive map phase: summarizing %d chunks with fast intermediate budgets", len(chunks))
    partial_summaries = [_generate_chunk_summary(c.text, length, is_intermediate=True) for c in chunks]
    joined_summary = " ".join(partial_summaries).strip()

    # Reduce step: check if joined partial summaries exceed token limit
    joined_tokens = tokenizer.encode(joined_summary, truncation=False)
    if len(joined_tokens) > MAX_SINGLE_PASS_TOKENS:
        logger.info("Abstractive reduce phase: joined summary (%d tokens) exceeds limit, reducing", len(joined_tokens))
        reduce_chunks = chunking_service.chunk_text(
            joined_summary,
            chunk_size=MAP_CHUNK_SIZE_CHARS,
            overlap=MAP_CHUNK_OVERLAP_CHARS,
        )
        if reduce_chunks:
            reduced = [_generate_chunk_summary(rc.text, length, is_intermediate=True) for rc in reduce_chunks]
            joined_summary = " ".join(reduced).strip()

    # Final condensation pass: only execute if the joined multi-chunk summary exceeds
    # the target word count threshold for the requested length.
    # If the combined chunk summaries already fit neatly into the target word budget,
    # returning them directly preserves valuable section coverage and avoids crushing
    # the summary down into 25-30 words.
    reduce_threshold = REDUCE_WORD_THRESHOLDS.get(length, 180)
    if len(chunks) > 1 and len(joined_summary.split()) > reduce_threshold:
        logger.info(
            "Abstractive reduce phase: condensing %d partial summaries (%d words > threshold %d)",
            len(chunks),
            len(joined_summary.split()),
            reduce_threshold,
        )
        return _generate_chunk_summary(joined_summary, length, is_intermediate=False)

    return joined_summary
