"""Tests for cleaning_service.

Non-ASCII characters are built with `chr()` rather than written literally. The
ones under test here (non-breaking space, curly quotes, soft hyphen) are either
invisible or indistinguishable from ASCII in a source file, which makes a
literal test data set unreviewable - and, on a Windows console, unprintable
when a test fails.
"""

import pytest

from app.services.cleaning_service import (
    EM_DASH,
    EN_DASH,
    ELLIPSIS,
    NBSP,
    SOFT_HYPHEN,
    clean_text,
    dehyphenate,
    normalise_characters,
    remove_page_number_lines,
    remove_repeated_lines,
    reflow,
)

LIGATURE_FI = chr(0xFB01)
LEFT_QUOTE = chr(0x201C)
RIGHT_QUOTE = chr(0x201D)
APOSTROPHE = chr(0x2019)
ZERO_WIDTH = chr(0x200B)


# --------------------------------------------------------------------------- #
# Character normalisation
# --------------------------------------------------------------------------- #
def test_curly_quotes_are_folded_to_ascii():
    """Regression: `str.translate` needs ordinal keys, not character keys.

    A dict keyed by single-character strings is silently ignored by
    `str.translate`, which quietly turns this whole mapping into a no-op. The
    ligature and ellipsis cases would still pass, because NFKC handles those
    independently, so only an assertion like this one catches the mistake.
    """
    text = f"{LEFT_QUOTE}quoted{RIGHT_QUOTE} and it{APOSTROPHE}s fine"

    assert normalise_characters(text) == "\"quoted\" and it's fine"


def test_ligatures_and_typography_are_normalised():
    text = f"The {LIGATURE_FI}nal cost{EM_DASH}about 10{EN_DASH}20{APOSTROPHE}s{ELLIPSIS}"

    assert normalise_characters(text) == "The final cost-about 10-20's..."


def test_non_breaking_space_becomes_a_plain_space():
    assert normalise_characters(f"10{NBSP}kg") == "10 kg"


def test_invisible_characters_are_removed():
    assert normalise_characters(f"wo{ZERO_WIDTH}rd") == "word"


def test_control_characters_are_removed_but_newlines_survive():
    assert normalise_characters("a\x00b\x07c\nd") == "abc\nd"


# --------------------------------------------------------------------------- #
# Page numbers
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "line",
    ["Page 12", "Page 1 of 2", "page 3/10", "pg. 7", "p. 4", "- 12 -", "12 of 30"],
)
def test_labelled_page_numbers_are_removed(line):
    kept, removed = remove_page_number_lines(["content", line, "more content"])

    assert removed == 1
    assert line not in kept


@pytest.mark.parametrize("line", ["2024", "Table 1", "1.", "Section 5", "Fig. 2"])
def test_content_that_looks_numeric_is_kept(line):
    """A lone number, a list marker or a caption is not pagination."""
    kept, removed = remove_page_number_lines(["content", line, "more content"])

    assert removed == 0
    assert line in kept


def test_a_run_of_bare_numbers_is_treated_as_pagination():
    """Several bare numbers look like a run of pages, so they go; one does not."""
    run = ["Intro", "1", "body text", "2", "more body", "3", "End"]
    kept, removed = remove_page_number_lines(run)
    assert removed == 3
    assert kept == ["Intro", "body text", "more body", "End"]

    kept, removed = remove_page_number_lines(["Intro", "2024", "body text"])
    assert removed == 0


# --------------------------------------------------------------------------- #
# Running headers and footers
# --------------------------------------------------------------------------- #
def test_a_line_repeated_three_times_is_removed():
    lines = ["Confidential"] * 3 + ["real content here"]

    kept, removed = remove_repeated_lines(lines, min_repeats=3, max_chars=120)

    assert removed == 3
    assert kept == ["real content here"]


def test_a_line_repeated_twice_is_kept():
    """Two occurrences is not enough evidence; the default threshold is three."""
    kept, removed = remove_repeated_lines(["Note"] * 2, min_repeats=3, max_chars=120)

    assert removed == 0
    assert len(kept) == 2


def test_a_long_repeated_line_is_kept():
    """A repeated sentence is content, however often the document repeats it."""
    sentence = "Extractive summarization returns sentences from the source. " * 3
    lines = [sentence] * 5

    kept, removed = remove_repeated_lines(lines, min_repeats=3, max_chars=120)

    assert removed == 0


def test_comparison_ignores_case_and_extra_spacing():
    lines = ["Confidential", "CONFIDENTIAL ", "  confidential", "text"]

    kept, removed = remove_repeated_lines(lines, min_repeats=3, max_chars=120)

    assert removed == 3
    assert kept == ["text"]


# --------------------------------------------------------------------------- #
# De-hyphenation
# --------------------------------------------------------------------------- #
def test_a_word_broken_across_a_line_is_rejoined():
    text, joins = dehyphenate("summa-\nrization is the task")

    assert text == "summarization is the task"
    assert joins == 1


def test_a_soft_hyphen_at_a_line_break_also_rejoins():
    text, joins = dehyphenate(f"summa{SOFT_HYPHEN}\nrization")

    assert text == "summarization"
    assert joins == 1


def test_a_hyphen_before_a_capital_letter_is_kept():
    """A hyphen before an uppercase continuation is a real compound, not a wrap."""
    text, joins = dehyphenate("State-\nOf-The-Art design")

    assert text == "State-\nOf-The-Art design"
    assert joins == 0


def test_a_hyphenated_word_on_one_line_is_untouched():
    text, joins = dehyphenate("a well-known result")

    assert text == "a well-known result"
    assert joins == 0


def test_a_mid_word_soft_hyphen_is_dropped_without_joining():
    text, joins = dehyphenate(f"summa{SOFT_HYPHEN}rization")

    assert text == "summarization"
    assert joins == 0


# --------------------------------------------------------------------------- #
# Reflow
# --------------------------------------------------------------------------- #
def test_single_newlines_become_spaces_and_blank_lines_split_paragraphs():
    text = "the first line\ncontinues here\n\nA new paragraph\nstarts here"

    assert reflow(text) == (
        "the first line continues here\n\nA new paragraph starts here"
    )


def test_runs_of_whitespace_are_collapsed():
    assert reflow("too    many \t spaces") == "too many spaces"


# --------------------------------------------------------------------------- #
# clean_text
# --------------------------------------------------------------------------- #
def test_clean_text_runs_the_whole_pipeline():
    raw = (
        "Confidential\n"
        "Page 1 of 2\n"
        "summa-\n"
        "rization is the task.\n"
        "\n"
        "Confidential\n"
        "Page 2 of 2\n"
        f"The {LIGATURE_FI}nal {LEFT_QUOTE}result{RIGHT_QUOTE} is large.\n"
        "\n"
        "Confidential\n"
        "Page 3 of 3\n"
        "Done.\n"
    )

    cleaned = clean_text(raw)

    assert cleaned.text == (
        "summarization is the task.\n\nThe final \"result\" is large.\n\nDone."
    )
    # Three repeated headers plus three page numbers.
    assert cleaned.removed_line_count == 6
    assert cleaned.hyphenation_joins == 1
    assert cleaned.original_character_count == len(raw)
    assert cleaned.character_count == len(cleaned.text)


def test_clean_text_preserves_meaningful_content():
    raw = "2024\n\nA sentence about the year 2024.\n\nTable 1\n\nRows follow."

    cleaned = clean_text(raw)

    assert "2024" in cleaned.text
    assert "Table 1" in cleaned.text
    assert "A sentence about the year 2024." in cleaned.text


def test_clean_text_on_empty_input():
    cleaned = clean_text("")

    assert cleaned.text == ""
    assert cleaned.character_count == 0


def test_clean_text_is_stable_when_run_twice():
    """Cleaning already-clean text must not keep eroding it."""
    raw = "Paragraph one is here.\n\nParagraph two is here."

    once = clean_text(raw)
    twice = clean_text(once.text)

    assert twice.text == once.text
