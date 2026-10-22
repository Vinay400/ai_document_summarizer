"""Small text helpers used across services."""

import re

_WHITESPACE = re.compile(r"\s+")


def count_words(text: str) -> int:
    """Whitespace-delimited word count (matches a word processor's count)."""
    return len(text.split()) if text else 0


def count_characters(text: str) -> int:
    return len(text) if text else 0


def has_text(text: str) -> bool:
    """True if the string has real content, not just whitespace/punctuation.

    A scanned PDF yields a string of newlines rather than an empty string, so a
    plain `if text:` check would wrongly accept it.
    """
    if not text:
        return False
    return bool(re.search(r"[A-Za-z0-9]", text))


def make_preview(text: str, limit: int = 280) -> str:
    """A short one-line excerpt, so the UI can show what was actually read."""
    if not text:
        return ""
    collapsed = _WHITESPACE.sub(" ", text).strip()
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[:limit].rsplit(" ", 1)[0] + "..."
