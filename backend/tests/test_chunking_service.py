"""Tests for chunking_service: sentence segmentation and chunking.

The repair logic is tested directly against synthetic punkt output rather than
through punkt itself, so the assertions hold whether or not the punkt data is
installed. Tests of `chunk_text` use text whose sentences comfortably fit the
chunk size, because a sentence longer than the chunk is deliberately hard-split
and no longer behaves like a sentence.
"""

import pytest

from app.services import chunking_service as chunking
from app.services.chunking_service import (
    Chunk,
    _repair_splits,
    chunk_text,
    sentence_tokenizer,
    split_sentences,
)


@pytest.fixture
def regex_tokenizer(monkeypatch):
    """Force the fallback splitter, whatever this machine has installed."""
    monkeypatch.setattr(chunking, "_tokenizer_name", "regex")


def _prose(sentence_count: int = 40) -> str:
    """Distinct sentences, each comfortably shorter than the chunk size."""
    return " ".join(
        f"Statement number {i} carries a few more words in it." for i in range(sentence_count)
    )


# --------------------------------------------------------------------------- #
# Sentence segmentation
# --------------------------------------------------------------------------- #
def test_splits_a_simple_paragraph():
    assert split_sentences("One thing. Another thing! A third?") == [
        "One thing.",
        "Another thing!",
        "A third?",
    ]


def test_empty_and_whitespace_input_yield_nothing():
    assert split_sentences("") == []
    assert split_sentences("   \n\t ") == []


def test_a_sentence_without_terminal_punctuation_is_kept():
    assert split_sentences("no full stop here") == ["no full stop here"]


def test_abbreviations_do_not_end_a_sentence():
    """The behaviour that matters downstream: no fragment like "as shown in Fig."

    An extractive summarizer selects sentences verbatim, so a spurious split
    here can put a meaningless fragment into the summary.
    """
    text = (
        "However, as shown in Fig. 3, the results differ. "
        "Hybrid systems reduce this risk, i.e. they select first. "
        "Dr. Lin wrote to J. R. R. Tolkien about it."
    )

    sentences = split_sentences(text)

    assert len(sentences) == 3
    for sentence in sentences:
        assert not sentence.endswith(("Fig.", "i.e.", "e.g.", "Dr.", "J.", "R."))


def test_decimal_numbers_are_not_split():
    assert split_sentences("It covers 3.14 million records.") == [
        "It covers 3.14 million records."
    ]


def test_regex_fallback_segments_prose(regex_tokenizer):
    sentences = split_sentences(
        "The first sentence is here. The second one follows! Is a third present? Yes."
    )

    assert sentences == [
        "The first sentence is here.",
        "The second one follows!",
        "Is a third present?",
        "Yes.",
    ]


# --------------------------------------------------------------------------- #
# Repairing punkt's splits
# --------------------------------------------------------------------------- #
def test_repair_rejoins_a_split_abbreviation():
    assert _repair_splits(["However, as shown in Fig.", "3, the results differ."]) == [
        "However, as shown in Fig. 3, the results differ."
    ]


def test_repair_rejoins_a_dotted_abbreviation():
    assert _repair_splits(["reduce this risk, i.e.", "they select first."]) == [
        "reduce this risk, i.e. they select first."
    ]


def test_repair_rejoins_a_chain_of_initials():
    """Merging can expose another abbreviation; the repair must keep going."""
    assert _repair_splits(["J.", "R.", "R. Tolkien wrote it."]) == [
        "J. R. R. Tolkien wrote it."
    ]


def test_repair_rejoins_a_segment_that_opens_a_bracket():
    assert _repair_splits(["The model (see Table", "2) is large."]) == [
        "The model (see Table 2) is large."
    ]


def test_repair_leaves_real_sentence_boundaries_alone():
    sentences = ["One thing.", "Another thing.", "A third."]

    assert _repair_splits(sentences) == sentences


def test_repair_does_not_join_a_sentence_ending_in_an_ordinary_word():
    assert _repair_splits(["The report is complete.", "It was reviewed."]) == [
        "The report is complete.",
        "It was reviewed.",
    ]


# --------------------------------------------------------------------------- #
# Chunking
# --------------------------------------------------------------------------- #
def test_short_text_becomes_one_unchanged_chunk():
    chunks = chunk_text("Just one short sentence.", chunk_size=1000, overlap=100)

    assert len(chunks) == 1
    assert chunks[0].text == "Just one short sentence."
    assert chunks[0].index == 0
    assert chunks[0].sentence_count == 1


def test_empty_text_produces_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_no_sentence_is_lost():
    text = _prose()
    chunks = chunk_text(text, chunk_size=300, overlap=60)

    joined = " ".join(chunk.text for chunk in chunks)

    for sentence in split_sentences(text):
        assert sentence in joined, f"lost: {sentence!r}"


def test_chunks_respect_the_size_limit():
    chunks = chunk_text(_prose(), chunk_size=300, overlap=60)

    assert len(chunks) > 1
    assert all(chunk.character_count <= 300 for chunk in chunks)


def test_consecutive_chunks_are_bridged_by_a_whole_sentence():
    """The point of the overlap: the seam is not left bare."""
    chunks = chunk_text(_prose(), chunk_size=300, overlap=60)

    assert len(chunks) > 2
    for previous, following in zip(chunks, chunks[1:]):
        tail = split_sentences(previous.text)[-1]
        assert tail in following.text, "boundary between chunks was not bridged"


def test_a_zero_overlap_duplicates_nothing():
    chunks = chunk_text(_prose(), chunk_size=300, overlap=0)

    for previous, following in zip(chunks, chunks[1:]):
        assert split_sentences(previous.text)[-1] not in following.text


def test_overlap_is_carried_even_when_it_exceeds_the_budget():
    """A sentence that stops short of the boundary bridges nothing.

    With a budget smaller than the final sentence, the earlier behaviour was to
    skip back to shorter, older sentences - duplicating text already wholly in
    the previous chunk while leaving the seam bare - or to carry nothing at all.
    """
    sentence = "A deliberately long sentence that will not fit the overlap budget."
    text = " ".join(f"{i} {sentence}" for i in range(30))

    chunks = chunk_text(text, chunk_size=200, overlap=20)

    assert len(chunks) > 1
    for previous, following in zip(chunks, chunks[1:]):
        assert split_sentences(previous.text)[-1] in following.text


def test_a_sentence_longer_than_the_chunk_is_hard_split():
    text = "word " * 200

    chunks = chunk_text(text.strip(), chunk_size=100, overlap=0)

    assert len(chunks) > 1
    assert all(chunk.character_count <= 100 for chunk in chunks)


def test_an_absurd_overlap_is_clamped_rather_than_looping():
    """An overlap at or above the chunk size would prevent any progress."""
    chunks = chunk_text(_prose(10), chunk_size=200, overlap=500)

    assert chunks
    assert all(chunk.character_count <= 200 for chunk in chunks)


def test_a_non_positive_chunk_size_is_rejected():
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=0)
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=-5)


def test_chunk_exposes_its_length():
    chunk = Chunk(index=3, text="abcd", sentence_count=2)

    assert chunk.character_count == 4
    assert chunk.index == 3


def test_the_active_tokenizer_is_reported():
    assert sentence_tokenizer() in {"nltk-punkt", "regex"}
