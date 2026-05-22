"""Extended tests for claude_knowledge._utils."""

import json
from pathlib import Path

import pytest

from claude_knowledge import _config
from claude_knowledge._utils import (
    _compute_tf_idf,
    build_index_entry,
    count_inbound_links,
    file_hash,
    get_article_word_count,
    get_knowledge_dir,
    list_raw_files,
    list_wiki_articles,
    load_state,
    read_all_wiki_content,
    read_wiki_index,
    save_state,
    wiki_article_exists,
)


class TestStateRoundTrip:
    """Test load_state and save_state."""

    def test_save_and_load(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """State save/load round-trip preserves data."""
        monkeypatch.setattr(_config, "REPORTS_STATE", tmp_path / "state")
        monkeypatch.setattr(_config, "STATE_FILE", tmp_path / "state" / "state.json")

        original = {"ingested": {"file.md": "hash"}, "query_count": 5, "total_cost": 1.23}
        save_state(original)
        loaded = load_state()
        assert loaded == original

    def test_load_default_state(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """load_state returns default when file missing."""
        monkeypatch.setattr(_config, "STATE_FILE", tmp_path / "missing.json")
        result = load_state()
        assert result["ingested"] == {}
        assert result["query_count"] == 0
        assert result["total_cost"] == 0.0

    def test_load_existing_state(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """load_state reads existing file."""
        monkeypatch.setattr(_config, "STATE_FILE", tmp_path / "state.json")
        (tmp_path / "state.json").write_text(json.dumps({"query_count": 42}))
        result = load_state()
        assert result["query_count"] == 42


class TestFileHash:
    """Test file_hash function."""

    def test_hash_length(self, tmp_path: Path) -> None:
        """Hash is 16 hex characters."""
        f = tmp_path / "test.txt"
        f.write_text("hello")
        result = file_hash(f)
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_hash_differentiates(self, tmp_path: Path) -> None:
        """Different content produces different hashes."""
        f1 = tmp_path / "a.txt"
        f1.write_text("alpha")
        f2 = tmp_path / "b.txt"
        f2.write_text("beta")
        assert file_hash(f1) != file_hash(f2)

    def test_hash_consistent(self, tmp_path: Path) -> None:
        """Same content produces same hash."""
        f = tmp_path / "test.txt"
        f.write_text("consistent")
        assert file_hash(f) == file_hash(f)


class TestWikiHelpers:
    """Test wiki content helpers."""

    def test_wiki_article_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """wiki_article_exists checks file on disk."""
        monkeypatch.setattr(_config, "KNOWLEDGE_DIR", tmp_path)
        (tmp_path / "existing.md").write_text("# Existing")
        assert wiki_article_exists("existing") is True
        assert wiki_article_exists("missing") is False

    def test_read_wiki_index_existing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """read_wiki_index returns content when file exists."""
        monkeypatch.setattr(_config, "INDEX_FILE", tmp_path / "index.md")
        (tmp_path / "index.md").write_text("# Custom Index\n")
        result = read_wiki_index()
        assert "Custom Index" in result

    def test_read_wiki_index_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """read_wiki_index returns default when file missing."""
        monkeypatch.setattr(_config, "INDEX_FILE", tmp_path / "missing.md")
        result = read_wiki_index()
        assert "Knowledge Base Index" in result

    def test_read_all_wiki_content(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """read_all_wiki_content aggregates index + articles."""
        monkeypatch.setattr(_config, "KNOWLEDGE_DIR", tmp_path)
        monkeypatch.setattr(_config, "INDEX_FILE", tmp_path / "index.md")
        monkeypatch.setattr(_config, "CONCEPTS_DIR", tmp_path / "concepts")
        monkeypatch.setattr(_config, "CONNECTIONS_DIR", tmp_path / "connections")
        monkeypatch.setattr(_config, "QA_DIR", tmp_path / "qa")
        (tmp_path / "index.md").write_text("# Index\n")
        (tmp_path / "concepts").mkdir()
        (tmp_path / "concepts" / "test.md").write_text("# Test\n")
        result = read_all_wiki_content()
        assert "## INDEX" in result
        assert "## concepts/test.md" in result
        assert "# Test" in result

    def test_read_all_wiki_content_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """read_all_wiki_content handles empty knowledge base."""
        monkeypatch.setattr(_config, "KNOWLEDGE_DIR", tmp_path)
        monkeypatch.setattr(_config, "INDEX_FILE", tmp_path / "index.md")
        monkeypatch.setattr(_config, "CONCEPTS_DIR", tmp_path / "concepts")
        monkeypatch.setattr(_config, "CONNECTIONS_DIR", tmp_path / "connections")
        monkeypatch.setattr(_config, "QA_DIR", tmp_path / "qa")
        (tmp_path / "index.md").write_text("# Index\n")
        result = read_all_wiki_content()
        assert "## INDEX" in result
        assert "---" not in result  # No articles means no separator

    def test_list_wiki_articles(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """list_wiki_articles returns all markdown files."""
        monkeypatch.setattr(_config, "CONCEPTS_DIR", tmp_path / "concepts")
        monkeypatch.setattr(_config, "CONNECTIONS_DIR", tmp_path / "connections")
        monkeypatch.setattr(_config, "QA_DIR", tmp_path / "qa")
        (tmp_path / "concepts").mkdir()
        (tmp_path / "concepts" / "a.md").write_text("A")
        result = list_wiki_articles()
        assert len(result) == 1
        assert result[0].name == "a.md"

    def test_list_raw_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """list_raw_files returns daily log files."""
        monkeypatch.setattr(_config, "DAILY_DIR", tmp_path / "daily")
        (tmp_path / "daily").mkdir()
        (tmp_path / "daily" / "2026-05-22.md").write_text("Log")
        result = list_raw_files()
        assert len(result) == 1
        assert result[0].name == "2026-05-22.md"

    def test_list_raw_files_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """list_raw_files returns empty when daily dir missing."""
        monkeypatch.setattr(_config, "DAILY_DIR", tmp_path / "nonexistent")
        result = list_raw_files()
        assert result == []


class TestCountInboundLinks:
    """Test count_inbound_links."""

    def test_counts_links(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """count_inbound_links finds wikilink references."""
        monkeypatch.setattr(_config, "CONCEPTS_DIR", tmp_path / "concepts")
        monkeypatch.setattr(_config, "CONNECTIONS_DIR", tmp_path / "connections")
        monkeypatch.setattr(_config, "QA_DIR", tmp_path / "qa")
        (tmp_path / "concepts").mkdir()
        (tmp_path / "concepts" / "a.md").write_text("See [[target]] for more.")
        (tmp_path / "concepts" / "b.md").write_text("Also see [[target|alias]].")
        result = count_inbound_links("target")
        assert result == 2

    def test_excludes_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """count_inbound_links respects exclude_file."""
        monkeypatch.setattr(_config, "CONCEPTS_DIR", tmp_path / "concepts")
        monkeypatch.setattr(_config, "CONNECTIONS_DIR", tmp_path / "connections")
        monkeypatch.setattr(_config, "QA_DIR", tmp_path / "qa")
        (tmp_path / "concepts").mkdir()
        a = tmp_path / "concepts" / "a.md"
        a.write_text("See [[target]] for more.")
        b = tmp_path / "concepts" / "b.md"
        b.write_text("Also see [[target|alias]].")
        result = count_inbound_links("target", exclude_file=b)
        assert result == 1


class TestTfIdfEdgeCases:
    """Test _compute_tf_idf edge cases."""

    def test_empty_corpus(self) -> None:
        """Empty corpus returns empty vectors and idf."""
        vectors, idf = _compute_tf_idf([])
        assert vectors == {}
        assert idf == {}

    def test_single_document(self) -> None:
        """Single document produces TF-IDF with log(2/2)+1 = 1 IDF."""
        vectors, idf = _compute_tf_idf([("doc1", "hello world")])
        assert "doc1" in vectors
        assert "hello" in idf
        assert idf["hello"] == pytest.approx(1.0, rel=0.01)

    def test_multiple_documents(self) -> None:
        """Multiple documents with shared and unique terms."""
        vectors, idf = _compute_tf_idf([
            ("doc1", "hello world foo"),
            ("doc2", "hello bar baz"),
        ])
        assert "doc1" in vectors
        assert "doc2" in vectors
        # Shared term "hello" should have lower IDF than unique terms
        assert idf["hello"] < idf["foo"]
        assert idf["hello"] < idf["bar"]


class TestBuildIndexEntry:
    """Test build_index_entry."""

    def test_format(self) -> None:
        """Produces correct markdown table row."""
        result = build_index_entry("concepts/test.md", "Summary", "source.md", "2026-05-22")
        assert "| [[concepts/test]] | Summary | source.md | 2026-05-22 |" == result


class TestGetKnowledgeDir:
    """Test get_knowledge_dir."""

    def test_returns_path(self) -> None:
        """Returns a Path object."""
        result = get_knowledge_dir()
        assert isinstance(result, Path)


class TestGetArticleWordCount:
    """Test get_article_word_count."""

    def test_basic_count(self, tmp_path: Path) -> None:
        """Counts words excluding frontmatter."""
        f = tmp_path / "article.md"
        f.write_text("---\ntitle: Test\n---\n\nHello world foo bar.")
        result = get_article_word_count(f)
        assert result == 4

    def test_no_frontmatter(self, tmp_path: Path) -> None:
        """Counts all words when no frontmatter."""
        f = tmp_path / "article.md"
        f.write_text("One two three four five.")
        result = get_article_word_count(f)
        assert result == 5
