"""Tests for claude_knowledge.ingest."""

import pytest
from pathlib import Path
import json

from claude_knowledge.ingest import _file_hash, _parse_frontmatter, ingest_dir


class TestFileHash:
    """Test _file_hash function."""

    def test_file_hash_basic(self, tmp_path: Path) -> None:
        """Test basic file hash computation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")
        result = _file_hash(test_file)
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_file_hash_consistent(self, tmp_path: Path) -> None:
        """Test that hash is consistent for same content."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        hash1 = _file_hash(test_file)
        hash2 = _file_hash(test_file)
        assert hash1 == hash2

    def test_file_hash_different_content(self, tmp_path: Path) -> None:
        """Test that different content produces different hashes."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("Content A")
        file2.write_text("Content B")
        assert _file_hash(file1) != _file_hash(file2)


class TestParseFrontmatter:
    """Test _parse_frontmatter function."""

    def test_no_frontmatter(self) -> None:
        """Test content without frontmatter."""
        content = "Just plain content"
        meta, body = _parse_frontmatter(content)
        assert meta == {}
        assert body == "Just plain content"

    def test_empty_frontmatter(self) -> None:
        """Test content with empty frontmatter."""
        content = "---\n---\nBody content"
        meta, body = _parse_frontmatter(content)
        assert meta == {}
        assert body == "\nBody content"

    def test_with_frontmatter(self) -> None:
        """Test content with valid frontmatter."""
        content = """---
title: Test Article
tags:
  - python
  - testing
---
Body content here"""
        meta, body = _parse_frontmatter(content)
        assert meta == {"title": "Test Article", "tags": ["python", "testing"]}
        assert body == "\nBody content here"

    def test_no_closing_fence(self) -> None:
        """Test content with opening but no closing fence."""
        content = "---\ntitle: Test\nBody content"
        meta, body = _parse_frontmatter(content)
        assert meta == {}
        assert body == content

    def test_invalid_yaml_frontmatter(self) -> None:
        """Test content with invalid YAML in frontmatter."""
        content = "---\nthis: is: invalid: yaml\n---\nBody"
        meta, body = _parse_frontmatter(content)
        assert meta == {}
        assert body == content

    def test_frontmatter_not_dict(self) -> None:
        """Test frontmatter that parses to non-dict."""
        content = "---\n- list item\n---\nBody"
        meta, body = _parse_frontmatter(content)
        assert meta == {}
        assert body == "\nBody"


class TestIngestDir:
    """Test ingest_dir function."""

    def test_basic_ingestion(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test basic markdown file ingestion."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "test.md").write_text("# Test\n\nContent here")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge.ingest.get_knowledge_dir", lambda: mock_kb_dir)

        result = ingest_dir(source_dir, dry_run=True)

        assert result["ingested"] == 1
        assert result["unchanged"] == 0
        assert result["errors"] == []

        artifacts_dir = mock_kb_dir / "artifacts"
        assert artifacts_dir.exists()
        artifact_files = list(artifacts_dir.glob("*.json"))
        assert len(artifact_files) == 1

    def test_ingestion_with_frontmatter(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test markdown file with frontmatter ingestion."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "article.md").write_text("""---
title: My Article
date: 2024-01-01
---

# Article Content

Some text here.""")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge.ingest.get_knowledge_dir", lambda: mock_kb_dir)

        result = ingest_dir(source_dir, dry_run=True)

        assert result["ingested"] == 1
        assert result["unchanged"] == 0

        artifact = list(mock_kb_dir.joinpath("artifacts").glob("*.json"))[0]
        data = json.loads(artifact.read_text())
        assert data["meta"]["title"] == "My Article"
        assert "# Article Content" in data["body"]

    def test_no_files_to_ingest(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test ingestion when source directory is empty."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge.ingest.get_knowledge_dir", lambda: mock_kb_dir)

        result = ingest_dir(source_dir, dry_run=True)

        assert result["ingested"] == 0
        assert result["unchanged"] == 0
        assert result["errors"] == []

    def test_chained_ingestion_unchanged(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that re-ingestion of unchanged files returns unchanged count."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "test.md").write_text("# Test Content")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge.ingest.get_knowledge_dir", lambda: mock_kb_dir)

        result1 = ingest_dir(source_dir)
        assert result1["ingested"] == 1

        result2 = ingest_dir(source_dir)
        assert result2["unchanged"] == 1
        assert result2["ingested"] == 0

    def test_force_all_ignores_state(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test force_all flag re-ingests all files."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "test.md").write_text("# Test Content")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge.ingest.get_knowledge_dir", lambda: mock_kb_dir)

        result1 = ingest_dir(source_dir)
        assert result1["ingested"] == 1

        result2 = ingest_dir(source_dir, force_all=True)
        assert result2["ingested"] == 1
        assert result2["unchanged"] == 0

    def test_state_persistence(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that state is persisted to state.json."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "test1.md").write_text("# Test 1")
        (source_dir / "test2.md").write_text("# Test 2")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge.ingest.get_knowledge_dir", lambda: mock_kb_dir)

        ingest_dir(source_dir)

        state_file = mock_kb_dir / "ingest_state.json"
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert "test1.md" in state
        assert "test2.md" in state

    def test_nested_directory_ingestion(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test ingestion of files in subdirectories."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        subdir = source_dir / "subdir"
        subdir.mkdir()
        (source_dir / "root.md").write_text("# Root")
        (subdir / "nested.md").write_text("# Nested")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge.ingest.get_knowledge_dir", lambda: mock_kb_dir)

        result = ingest_dir(source_dir, dry_run=True)

        assert result["ingested"] == 2

    def test_non_markdown_files_ignored(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that non-markdown files are not ingested."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "test.py").write_text("# Python file")
        (source_dir / "test.md").write_text("# Markdown file")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge.ingest.get_knowledge_dir", lambda: mock_kb_dir)

        result = ingest_dir(source_dir, dry_run=True)

        assert result["ingested"] == 1

    def test_os_error_handling(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test error handling when file read fails."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        test_file = source_dir / "test.md"
        test_file.write_text("# Test")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge.ingest.get_knowledge_dir", lambda: mock_kb_dir)

        test_file.chmod(0o000)

        try:
            result = ingest_dir(source_dir, dry_run=True)
            assert len(result["errors"]) > 0
        finally:
            test_file.chmod(0o644)
