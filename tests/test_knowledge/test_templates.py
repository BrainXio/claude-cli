"""Tests for claude_knowledge.templates."""

import pytest

from claude_knowledge.templates import get_template, list_types, scaffold_article


def test_list_types() -> None:
    types = list_types()
    assert "concept" in types
    assert "mechanism" in types
    assert "outcome" in types
    assert "reference" in types
    assert "connection" in types


def test_get_template_known() -> None:
    tpl = get_template("concept")
    assert tpl is not None
    assert "title" in tpl["required_frontmatter"]


def test_get_template_unknown() -> None:
    assert get_template("nonexistent") is None


def test_scaffold_article() -> None:
    md = scaffold_article("concept", "Test Concept", tags=["example"])
    assert "---" in md
    assert "title: Test Concept" in md
    assert "type: concept" in md
    assert "## Definition" in md


def test_scaffold_article_unknown_type_raises() -> None:
    with pytest.raises(ValueError):
        scaffold_article("unknown", "Title")
