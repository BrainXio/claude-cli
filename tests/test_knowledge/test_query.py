"""Tests for claude_knowledge.query."""

import pytest

from claude_knowledge._utils import _compute_tf_idf
from claude_knowledge.query import _cosine_similarity
from claude_knowledge._utils import _tokenize


def test_tokenize() -> None:
    tokens = _tokenize("Hello world, this is a TEST!")
    assert "hello" in tokens
    assert "world" in tokens
    assert "test" in tokens
    assert "a" not in tokens  # too short


def test_compute_tf_idf() -> None:
    docs = [
        ("doc1", "hello world foo"),
        ("doc2", "hello bar baz"),
    ]
    vectors, idf = _compute_tf_idf(docs)
    assert "doc1" in vectors
    assert "doc2" in vectors
    assert "hello" in idf  # appears in both docs
    assert idf["hello"] < idf["foo"]  # common term has lower IDF


def test_cosine_similarity_identical() -> None:
    vec = {"a": 1.0, "b": 1.0}
    assert _cosine_similarity(vec, vec) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal() -> None:
    vec1 = {"a": 1.0}
    vec2 = {"b": 1.0}
    assert _cosine_similarity(vec1, vec2) == 0.0
