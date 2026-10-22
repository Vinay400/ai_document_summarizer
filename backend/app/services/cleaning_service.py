"""
Text cleaning for extracted documents.

Extraction (Phases 2-3) returns what the file literally contains, which is not
what a summarizer wants to read:

* a PDF page is a grid of lines, so every wrapped line ends in a newline that
  carries no meaning;
* a word broken across two lines keeps its hyphen ("summa-\\nrization");
* running headers, footers and page numbers repeat on every page;
* one character can arrive as several code points (ligatures, curly quotes,
  non-breaking spaces), so a ligature "fi" does not compare equal to a typed
  "fi".

This module turns that into flowing prose. It is deliberately conservative: a
line is only removed when it is structurally meaningless (a page number) or
provably repeated (a running header), because deleting real content is a far
worse failure than leaving a stray footer behind.

`clean_text` is the only entry point callers need. The steps it composes are
separate functions over a list of lines so each can be tested on its own.

Non-ASCII characters are written with `chr()` throughout. Several of the ones
handled here are invisible or indistinguishable from ASCII in source, and a
literal non-breaking space in this file would be a trap for the next editor.
"""

import logging
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)

# Paragraphs are separated by a blank line, matching document_service's
# BLOCK_SEPARATOR, so cleaning neither invents nor destroys block boundaries.
PARAGRAPH_SEPARATOR = "\n\n"

# Characters that matter below, named once so the intent is readable.
NBSP = chr(0x00A0)
FIGURE_SPACE = chr(0x2007)
NARROW_NBSP = chr(0x202F)
EN_DASH = chr(0x2013)
EM_DASH = chr(0x2014)
SOFT_HYPHEN = chr(0x00AD)
MINUS_SIGN = chr(0x2212)
ELLIPSIS = chr(0x2026)


@dataclass
class CleanedText:
    """The cleaned text plus what changed, so the effect is visible, not silent."""

    text: str
    original_character_count: int
    original_line_count: int
    removed_line_count: int = 0
    hyphenation_joins: int = 0

    @property
    def character_count(self) -> int:
        return len(self.text)


# --------------------------------------------------------------------------- #
# Step 1 - character normalisation
# --------------------------------------------------------------------------- #
# NFKC folds the compatibility cases: ligatures (fi, fl, ffi), full-width forms
# and superscripts - and, less obviously, non-breaking spaces and the ellipsis,
# both of which have compatibility decompositions. The replacements below are
# the ones NFKC does *not* handle, chiefly curly quotes and en/em dashes.
#
# `str.maketrans` is required, not cosmetic: `str.translate` looks up ordinals,
# so a dict keyed by single-character strings is silently ignored - every entry
# here would be a no-op.
_CHARACTER_MAP = str.maketrans(
    {
        NBSP: " ",
        FIGURE_SPACE: " ",
        NARROW_NBSP: " ",
        chr(0x2018): "'",  # curly single quotes...
        chr(0x2019): "'",
        chr(0x201A): "'",
        chr(0x201B): "'",
        chr(0x201C): '"',  # ...and double quotes
        chr(0x201D): '"',
        chr(0x201E): '"',
        EN_DASH: "-",
        EM_DASH: "-",
        MINUS_SIGN: "-",
        ELLIPSIS: "...",
    }
)

# Removed outright: zero-width marks, word joiner and the byte-order mark.
# Invisible, but they split tokens and defeat n-gram matching.
_INVISIBLE = dict.fromkeys([0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF], None)

# Keep tab and newline; drop the remaining C0 controls and DEL.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def normalise_characters(text: str) -> str:
    """Fold equivalent code points together so later matching is reliable.

    Quote and dash normalisation is not cosmetic. Evaluation compares generated
    summaries against a reference, and "don't" spelled with a curly apostrophe
    will not match "don't" spelled with a straight one.

    Soft hyphens survive this step on purpose: the de-hyphenation step needs to
    see them to know a word was broken.
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_INVISIBLE)
    text = text.translate(_CHARACTER_MAP)
    return _CONTROL_CHARS.sub("", text)


# --------------------------------------------------------------------------- #
# Step 2 - page numbers
# --------------------------------------------------------------------------- #
# Bare digits are the dangerous case: "2024" alone on a line may be real content
# (a year, a table cell). A lone number is therefore only treated as pagination
# when several appear, which is what a run of pages looks like. Labelled forms
# ("Page 12") are unambiguous and always removed.
_DASHES = f"{EN_DASH}{EM_DASH}"
_PAGE_LABEL = re.compile(
    r"^\s*(?:page|pg\.?|p\.)\s*\d{1,4}(?:\s*(?:of|/)\s*\d{1,4})?\s*$",
    re.IGNORECASE,
)
_PAGE_OF_TOTAL = re.compile(r"^\s*\d{1,4}\s*(?:of|/)\s*\d{1,4}\s*$")
_PAGE_DECORATED = re.compile(
    rf"^\s*[-{_DASHES}]\s*\d{{1,4}}\s*[-{_DASHES}]\s*$"
)
_BARE_NUMBER = re.compile(r"^\s*\d{1,4}\s*$")

# Below this many bare-number lines they are assumed to be content, not pages.
MIN_BARE_NUMBERS = 3


def _is_page_number(line: str, bare_numbers: int) -> bool:
    if _PAGE_LABEL.match(line) or _PAGE_OF_TOTAL.match(line):
        return True
    if _PAGE_DECORATED.match(line):
        return True
    return bare_numbers >= MIN_BARE_NUMBERS and _BARE_NUMBER.match(line) is not None


def remove_page_number_lines(lines: list[str]) -> tuple[list[str], int]:
    """Drop lines that are a page number and nothing else."""
    bare_numbers = sum(1 for line in lines if _BARE_NUMBER.match(line))
    kept = [line for line in lines if not _is_page_number(line, bare_numbers)]
    return kept, len(lines) - len(kept)


# --------------------------------------------------------------------------- #
# Step 3 - running headers and footers
# --------------------------------------------------------------------------- #
def _comparable(line: str) -> str:
    """The form two lines are compared in: case- and spacing-insensitive."""
    return re.sub(r"\s+", " ", line).strip().casefold()


def remove_repeated_lines(
    lines: list[str], min_repeats: int, max_chars: int
) -> tuple[list[str], int]:
    """Drop short lines that recur throughout the document.

    A header or footer is the same text on every page, so exact repetition is
    strong evidence. Restricting to short lines keeps genuine content safe: a
    sentence that happens to repeat is still content, however often it occurs.

    Only *exact* repeats are caught. A footer whose text changes per page
    ("Report 2024 - page 3") is missed, unless the changing part is the whole
    line, in which case the page-number step above deals with it. That blind
    spot is deliberate - masking the digits would also delete genuinely
    numbered short lines such as a run of table captions.
    """
    comparable = [_comparable(line) for line in lines]
    counts = Counter(
        text for text in comparable if text and len(text) <= max_chars
    )
    repeated = {text for text, count in counts.items() if count >= min_repeats}

    kept = [
        line
        for line, text in zip(lines, comparable)
        if not (text in repeated and len(text) <= max_chars)
    ]
    return kept, len(lines) - len(kept)


# --------------------------------------------------------------------------- #
# Step 4 - de-hyphenation
# --------------------------------------------------------------------------- #
# A word broken across a line keeps its hyphen: "summa-\nrization". The join is
# only safe when the continuation starts lowercase, which is what distinguishes
# a broken word from a real compound ("State-\nOf-The-Art").
_BROKEN_WORD = re.compile(
    rf"([A-Za-z])[{re.escape(SOFT_HYPHEN)}-][ \t]*\n[ \t]*([a-z])"
)


def dehyphenate(text: str) -> tuple[str, int]:
    """Rejoin words split across a line break. Returns `(text, joins)`."""
    joins = 0

    def join(match: re.Match) -> str:
        nonlocal joins
        joins += 1
        return match.group(1) + match.group(2)

    text = _BROKEN_WORD.sub(join, text)

    # Any soft hyphen left was mid-word on a single line, where it is purely a
    # display hint and carries no characters of its own.
    return text.replace(SOFT_HYPHEN, ""), joins


# --------------------------------------------------------------------------- #
# Step 5 - reflow
# --------------------------------------------------------------------------- #
def reflow(text: str) -> str:
    """Turn a grid of lines back into paragraphs.

    Blank lines are honoured as paragraph breaks; a single newline is only a
    line wrap, so it becomes a space. Splitting each paragraph on whitespace
    also collapses runs of spaces and tabs, which is why no separate whitespace
    step is needed.
    """
    paragraphs = re.split(r"\n[ \t]*\n", text)
    joined = (" ".join(paragraph.split()) for paragraph in paragraphs)
    return PARAGRAPH_SEPARATOR.join(part for part in joined if part)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def clean_text(text: str) -> CleanedText:
    """Clean extracted text, keeping only structure that carries meaning.

    The order matters: de-hyphenation needs the original line breaks, so it runs
    before `reflow` removes them.
    """
    original_character_count = len(text)
    lines = normalise_characters(text).split("\n")
    original_line_count = len(lines)

    lines, page_number_lines = remove_page_number_lines(lines)

    header_lines = 0
    if settings.CLEAN_STRIP_HEADERS:
        lines, header_lines = remove_repeated_lines(
            lines, settings.HEADER_MIN_REPEATS, settings.HEADER_MAX_CHARS
        )

    reflowed, joins = dehyphenate("\n".join(lines))
    cleaned = reflow(reflowed)

    removed_line_count = page_number_lines + header_lines
    if removed_line_count or joins:
        logger.info(
            "Cleaning removed %d line(s) (%d page number, %d repeated) and "
            "rejoined %d hyphenated word(s)",
            removed_line_count,
            page_number_lines,
            header_lines,
            joins,
        )

    return CleanedText(
        text=cleaned,
        original_character_count=original_character_count,
        original_line_count=original_line_count,
        removed_line_count=removed_line_count,
        hyphenation_joins=joins,
    )
