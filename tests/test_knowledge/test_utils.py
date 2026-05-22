"""Tests for claude_knowledge._utils."""

from claude_knowledge._utils import _tokenize, extract_wikilinks, slugify


def test_tokenize_basic() -> None:
    tokens = _tokenize("The quick brown fox jumps over the lazy dog")
    assert "quick" in tokens
    assert "fox" in tokens
    assert "the" in tokens  # 3 characters, passes the >2 filter


def test_slugify() -> None:
    assert slugify("Hello World!") == "hello-world"
    assert slugify("  Multiple   Spaces  ") == "multiple-spaces"
    assert slugify("UPPERCASE") == "uppercase"


def test_extract_wikilinks() -> None:
    content = "See [[Concept A]] and [[Concept B|alias]] for details."
    links = extract_wikilinks(content)
    assert links == ["Concept A", "Concept B"]
