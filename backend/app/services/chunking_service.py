"""
Sentence segmentation and sentence-aware chunking.

Chunking exists because of a hard model limit: BART reads 1024 tokens, so a
20-page document cannot be summarized in one pass. It must be split, summarized
piece by piece (map) and the results condensed (reduce). See the architecture
notes in the root README.

Two decisions shape this module:

* **Split on sentences, never mid-sentence.** A chunk that begins or ends in the
  middle of a sentence gives the summarizer a fragment, and fragments are what
  produce garbled output.
* **Overlap consecutive chunks.** Without it, a fact spanning a boundary is
  split across two chunks and may survive in neither. The overlap is measured in
  characters but applied on sentence boundaries, so it never cuts a sentence
  either.

Sentence segmentation uses NLTK's punkt model when its data is present, and a
regex splitter when it is not. Punkt is downloaded separately from the library
(`nltk.download('punkt_tab')`), exactly like the Tesseract binary, so a missing
model must degrade rather than crash. `sentence_tokenizer()` reports which one is
in use.
"""

import logging
import re
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)

_tokenizer_name: str | None = None


# --------------------------------------------------------------------------- #
# Sentence segmentation
# --------------------------------------------------------------------------- #
def sentence_tokenizer() -> str:
    """Name of the tokenizer in use: `'nltk-punkt'` or `'regex'`."""
    global _tokenizer_name
    if _tokenizer_name is None:
        _tokenizer_name = _probe_tokenizer()
    return _tokenizer_name


def reset_tokenizer_cache() -> None:
    """Forget the probe result. Used by tests."""
    global _tokenizer_name
    _tokenizer_name = None


def _probe_tokenizer() -> str:
    """Decide once whether punkt can be used.

    The probe actually tokenizes a string rather than only checking that the
    data files exist, because NLTK 3.9 moved to `punkt_tab` and a machine can
    easily have the older `punkt` present but not the newer one.
    """
    try:
        from nltk.tokenize import sent_tokenize

        sent_tokenize("Probe. Two sentences.")
    except Exception as exc:  # LookupError, ImportError, ...
        logger.warning(
            "NLTK punkt data is unavailable (%s); using the regex sentence "
            "splitter. Run nltk.download('punkt_tab') for better segmentation.",
            exc,
        )
        return "regex"
    return "nltk-punkt"


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, dropping empty results."""
    stripped = (text or "").strip()
    if not stripped:
        return []

    if sentence_tokenizer() == "nltk-punkt":
        from nltk.tokenize import sent_tokenize

        sentences = _repair_splits(sent_tokenize(stripped))
    else:
        sentences = _regex_split_sentences(stripped)

    return [sentence for sentence in (s.strip() for s in sentences) if sentence]


# Words that end in a full stop without ending a sentence.
_ABBREVIATIONS = frozenset(
    """
    mr mrs ms dr prof sr jr st vs etc inc ltd co corp gov sen rep gen col capt
    lt sgt fig eq ref no vol approx est al cf ed eds pp ph dist dept univ
    jan feb mar apr jun jul aug sep sept oct nov dec
    mon tue tues wed thu thur thurs fri sat sun
    """.split()
)

# Terminal punctuation, any closing quotes or brackets, then whitespace.
_BOUNDARY = re.compile(r"([.!?])([\"')\]]*)(\s+)")


def _is_false_boundary(text: str, match: re.Match) -> bool:
    """True if this full stop is part of an abbreviation, not a sentence end."""
    if match.group(1) != ".":
        return False  # "!" and "?" are unambiguous

    preceding = text[: match.start(1)]
    word = re.search(r"([A-Za-z]+|\d+)$", preceding)
    if word is None:
        return False

    token = word.group(1)
    if token.casefold() in _ABBREVIATIONS:
        return True

    if len(token) == 1:
        if token.isupper():
            return True  # an initial: "J. R. R. Tolkien"
        # A lone lowercase letter inside a dotted form: "e.g.", "i.e."
        if token.islower() and preceding[word.start() - 1 : word.start()] == ".":
            return True

    return False


def _regex_split_sentences(text: str) -> list[str]:
    """Fallback splitter for when punkt data is unavailable.

    Deliberately conservative: it breaks after terminal punctuation, except
    where the preceding token is a known abbreviation, an initial, or part of a
    dotted form. Decimals are safe automatically, because a full stop inside
    "3.14" is not followed by whitespace and so never matches the boundary.
    """
    sentences: list[str] = []
    start = 0

    for match in _BOUNDARY.finditer(text):
        if _is_false_boundary(text, match):
            continue
        sentence = text[start : match.end(2)].strip()
        if sentence:
            sentences.append(sentence)
        start = match.end(3)

    tail = text[start:].strip()
    if tail:
        sentences.append(tail)

    return sentences


# --------------------------------------------------------------------------- #
# Repairing punkt's splits
# --------------------------------------------------------------------------- #
# Punkt's English model is unsupervised, and its abbreviation set turns out to
# exclude some common ones: given "as shown in Fig. 3" it splits after "Fig.",
# and "reduce this risk, i.e. they select" after "i.e.". Those fragments are
# actively harmful downstream - an extractive summarizer can select
# "as shown in Fig." as a summary sentence - so the splits are rejoined using
# the same abbreviation knowledge the fallback splitter relies on.
_DOTTED_FORM = re.compile(r"[A-Za-z]\.[A-Za-z]\.")


def _ends_with_abbreviation(segment: str) -> bool:
    """True if this segment cannot really end where punkt ended it."""
    stripped = segment.rstrip().rstrip("\"')]")
    if not stripped.endswith("."):
        return False

    match = re.search(r"([A-Za-z.]+)$", stripped)
    if match is None:
        return False

    token = match.group(1)
    letters = token.replace(".", "")
    if not letters:
        return False

    if letters.casefold() in _ABBREVIATIONS:
        return True
    if _DOTTED_FORM.fullmatch(token):
        return True  # "e.g.", "i.e.", "a.m."
    return letters.isupper() and len(letters) == 1  # an initial: "J."


def _has_unclosed_bracket(segment: str) -> bool:
    """True if a bracket opened here was never closed."""
    return segment.count("(") > segment.count(")") or segment.count("[") > segment.count("]")


def _repair_splits(sentences: list[str]) -> list[str]:
    """Rejoin segments that punkt split at an abbreviation or mid-bracket.

    Repeated merging is intentional: "J. R. R. Tolkien" can arrive as several
    fragments, and each merge may reveal another abbreviation at the new end.
    """
    repaired: list[str] = []
    for sentence in sentences:
        if repaired and (
            _ends_with_abbreviation(repaired[-1]) or _has_unclosed_bracket(repaired[-1])
        ):
            repaired[-1] = f"{repaired[-1]} {sentence}"
        else:
            repaired.append(sentence)
    return repaired


# --------------------------------------------------------------------------- #
# Chunking
# --------------------------------------------------------------------------- #
@dataclass
class Chunk:
    """A slice of the document small enough to feed a model in one pass."""

    index: int
    text: str
    # Sentence segments joined into this chunk. A single sentence longer than
    # the chunk size is counted once per piece it was split into.
    sentence_count: int

    @property
    def character_count(self) -> int:
        return len(self.text)


def chunk_text(
    text: str, chunk_size: int | None = None, overlap: int | None = None
) -> list[Chunk]:
    """Split text into overlapping, sentence-aligned chunks.

    Every sentence in the input appears in at least one chunk. Overlap means
    text can appear in two chunks; nothing is ever dropped.
    """
    size = settings.CHUNK_SIZE if chunk_size is None else chunk_size
    budget = settings.CHUNK_OVERLAP if overlap is None else overlap

    if size <= 0:
        raise ValueError(f"chunk_size must be positive, got {size}")
    # The overlap must leave room for new content, or chunking could not
    # advance: a chunk that is all overlap carries nothing forward.
    budget = max(0, min(budget, size - 1))

    sentences = split_sentences(text)
    if not sentences:
        return []

    chunks: list[Chunk] = []
    current: list[str] = []

    for sentence in sentences:
        for piece in _split_oversized(sentence, size):
            if current and _joined_length(current) + 1 + len(piece) > size:
                chunks.append(_close(len(chunks), current))
                current = _overlap_tail(current, budget)
                # If the carried-over context leaves no room for this piece,
                # drop it: an overlap that blocks progress defeats its purpose.
                if _joined_length(current) + 1 + len(piece) > size:
                    current = []
            current.append(piece)

    if current:
        chunks.append(_close(len(chunks), current))

    logger.info(
        "Split %d sentence(s) into %d chunk(s) of up to %d characters",
        len(sentences),
        len(chunks),
        size,
    )
    return chunks


def _joined_length(sentences: list[str]) -> int:
    """Length of these sentences once joined, separators included."""
    return len(" ".join(sentences))


def _close(index: int, sentences: list[str]) -> Chunk:
    return Chunk(index=index, text=" ".join(sentences), sentence_count=len(sentences))


def _overlap_tail(sentences: list[str], budget: int) -> list[str]:
    """The trailing sentences to repeat at the start of the next chunk.

    Whole sentences only - carrying part of a sentence would reintroduce exactly
    the mid-sentence split this module exists to avoid.

    The final sentence is always carried when any overlap is requested, even if
    it alone exceeds `budget`. The purpose of an overlap is to bridge the
    boundary between two chunks, and a sentence that stops short of the boundary
    bridges nothing: skipping past it to shorter, older sentences duplicates
    text already wholly inside the previous chunk while leaving the seam bare.
    `budget` is therefore a target, not a hard cap. Older sentences are added
    only while they still fit.
    """
    if budget <= 0 or not sentences:
        return []

    taken = [sentences[-1]]
    total = len(sentences[-1])

    for sentence in reversed(sentences[:-1]):
        cost = len(sentence) + 1  # + the joining space
        if total + cost > budget:
            break
        taken.insert(0, sentence)
        total += cost

    return taken


def _split_oversized(sentence: str, limit: int) -> list[str]:
    """Break a sentence longer than `limit` on word boundaries.

    Rare, but a single unbroken "sentence" - a table row, a mangled OCR line
    with no punctuation - would otherwise produce a chunk no model can accept.
    """
    if len(sentence) <= limit:
        return [sentence]

    pieces: list[str] = []
    current = ""
    for word in sentence.split():
        if current and len(current) + 1 + len(word) > limit:
            pieces.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()

    if current:
        pieces.append(current)
    return pieces or [sentence[:limit]]
