"""Tests for claude_knowledge.index."""

import json
import os
from pathlib import Path

import pytest

from claude_knowledge.index import build_index, load_index, index_is_stale


class TestBuildIndex:
    """Test build_index function."""

    def test_build_empty_index(self, tmp_path: Path) -> None:
        """Test building an empty index."""
        index_path = tmp_path / "index.json"

        result = build_index([], index_path)

        assert "version" in result
        assert result["version"] == 1
        assert "corpus_hash" in result
        assert result["document_count"] == 0
        assert "idf" in result
        assert result["idf"] == {}
        assert "vectors" in result
        assert result["vectors"] == {}

        # Verify file was written
        assert index_path.exists()

    def test_build_index_with_documents(self, tmp_path: Path) -> None:
        """Test building an index with documents."""
        index_path = tmp_path / "index.json"
        documents = [
            ("doc1", "hello world foo"),
            ("doc2", "hello bar baz"),
        ]

        result = build_index(documents, index_path)

        assert "version" in result
        assert result["document_count"] == 2
        assert "corpus_hash" in result
        assert len(result["corpus_hash"]) == 16
        assert "idf" in result
        assert "hello" in result["idf"]
        assert "foo" in result["idf"]
        assert "bar" in result["idf"]
        assert "vectors" in result
        assert "doc1" in result["vectors"]
        assert "doc2" in result["vectors"]

    def test_build_index_persists_to_file(self, tmp_path: Path) -> None:
        """Test that index is persisted to file."""
        index_path = tmp_path / "index.json"
        documents = [
            ("doc1", "hello world"),
        ]

        build_index(documents, index_path)

        content = json.loads(index_path.read_text())
        assert content["version"] == 1
        assert content["document_count"] == 1
        assert content["corpus_hash"] is not None

    def test_build_index_default_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that default path uses KNOWLEDGE_DIR."""
        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)

        documents = [
            ("doc1", "test content"),
        ]

        result = build_index(documents)

        index_path = mock_kb_dir / "index_cache.json"
        assert index_path.exists()
        assert result["document_count"] == 1

    def test_build_index_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that parent directories are created if they don't exist."""
        index_path = tmp_path / "nested" / "path" / "index.json"

        result = build_index([], index_path)

        assert index_path.exists()
        assert result["document_count"] == 0


class TestLoadIndex:
    """Test load_index function."""

    def test_load_nonexistent_index(self, tmp_path: Path) -> None:
        """Test loading a non-existent index."""
        index_path = tmp_path / "nonexistent.json"
        result = load_index(index_path)
        assert result is None

    def test_load_index_default_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading index from default path."""
        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)

        index_path = mock_kb_dir / "index_cache.json"
        documents = [("doc1", "test content")]
        build_index(documents)

        result = load_index()
        assert result is not None
        assert result["document_count"] == 1

    def test_load_existing_index(self, tmp_path: Path) -> None:
        """Test loading an existing index file."""
        index_path = tmp_path / "index.json"
        documents = [
            ("doc1", "hello world"),
        ]
        build_index(documents, index_path)

        result = load_index(index_path)
        assert result is not None
        assert result["document_count"] == 1
        assert "vectors" in result

    def test_load_invalid_json_returns_none(self, tmp_path: Path) -> None:
        """Test that invalid JSON returns None."""
        index_path = tmp_path / "index.json"
        index_path.write_text("not valid json")

        result = load_index(index_path)
        assert result is None

    def test_load_empty_json_returns_none(self, tmp_path: Path) -> None:
        """Test that empty JSON returns None."""
        index_path = tmp_path / "index.json"
        index_path.write_text("")

        result = load_index(index_path)
        assert result is None

    def test_load_missing_fields(self, tmp_path: Path) -> None:
        """Test loading an index with missing fields."""
        index_path = tmp_path / "index.json"
        # Write an index with minimal data
        index_path.write_text('{"version": 1}')

        result = load_index(index_path)
        assert result is not None
        assert result["version"] == 1


class TestIndexIsStale:
    """Test index_is_stale function."""

    def test_stale_no_index(self, tmp_path: Path) -> None:
        """Test that index is stale when no index exists."""
        index_path = tmp_path / "index.json"

        result = index_is_stale([], index_path)
        assert result is True

    def test_stale_different_corpus(self, tmp_path: Path) -> None:
        """Test that index is stale when corpus has changed."""
        index_path = tmp_path / "index.json"

        # Build initial index
        documents1 = [("doc1", "hello world foo")]
        build_index(documents1, index_path)

        # Check if current index is stale
        result = index_is_stale(documents1, index_path)
        assert result is False

        # Modify corpus
        documents2 = [("doc1", "different content")]
        result = index_is_stale(documents2, index_path)
        assert result is True

    def test_stale_same_corpus(self, tmp_path: Path) -> None:
        """Test that index is not stale when corpus is the same."""
        index_path = tmp_path / "index.json"

        documents = [("doc1", "hello world foo")]
        build_index(documents, index_path)

        # Same documents should not be stale
        result = index_is_stale(documents, index_path)
        assert result is False

    def test_stale_different_document_count(self, tmp_path: Path) -> None:
        """Test that index is stale when document count changes."""
        index_path = tmp_path / "index.json"

        # Build index with one document
        documents1 = [("doc1", "hello world")]
        build_index(documents1, index_path)

        # Add another document
        documents2 = [
            ("doc1", "hello world"),
            ("doc2", "new document"),
        ]

        result = index_is_stale(documents2, index_path)
        assert result is True

    def test_stale_default_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that default path uses KNOWLEDGE_DIR."""
        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)

        index_path = mock_kb_dir / "index_cache.json"
        documents = [("doc1", "test content")]
        build_index(documents)

        result = index_is_stale(documents)
        assert result is False

        # Modify documents
        modified = [("doc1", "modified content")]
        result = index_is_stale(modified)
        assert result is True
