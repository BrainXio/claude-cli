"""Tests for claude_knowledge.cli."""

import argparse
import json
from pathlib import Path

import pytest

from claude_knowledge import cli


class TestCmdIngest:
    """Test _cmd_ingest function."""

    def test_ingest_success(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        """Test successful ingest command."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "test.md").write_text("# Test")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge.ingest.get_knowledge_dir", lambda: mock_kb_dir)

        args = argparse.Namespace(
            source=str(source_dir),
            dry_run=True,
            force_all=False,
        )

        result = cli._cmd_ingest(args)

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["ingested"] == 1
        assert output["unchanged"] == 0
        assert output["errors"] == []

    def test_ingest_with_errors(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        """Test ingest command with errors."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "test.md").write_text("# Test")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge.ingest.get_knowledge_dir", lambda: mock_kb_dir)

        args = argparse.Namespace(
            source=str(source_dir),
            dry_run=False,
            force_all=False,
        )

        result = cli._cmd_ingest(args)

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "errors" in output


class TestCmdCompile:
    """Test _cmd_compile function."""

    def test_compile_success(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        """Test successful compile command."""
        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()
        (daily_dir / "2024-01-15.md").write_text("2024-01-15T10:00:00 Test")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._config.DAILY_DIR", daily_dir)

        args = argparse.Namespace(
            dry_run=True,
        )

        result = cli._cmd_compile(args)

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["compiled"] == 1
        assert output["errors"] == []

    def test_compile_with_errors(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        """Test compile command with errors."""
        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._config.DAILY_DIR", daily_dir)

        args = argparse.Namespace(
            dry_run=False,
        )

        result = cli._cmd_compile(args)

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "errors" in output


class TestCmdQuery:
    """Test _cmd_query function."""

    def test_query_success(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        """Test successful query command with text output."""
        mock_kb_dir = tmp_path / "knowledge"
        articles_dir = mock_kb_dir / "articles"
        articles_dir.mkdir(parents=True)

        (articles_dir / "test.json").write_text(
            json.dumps({"entries": [{"body": "Test content about python"}]})
        )

        monkeypatch.setattr("claude_knowledge.query.KNOWLEDGE_DIR", mock_kb_dir)

        args = argparse.Namespace(
            question="python",
            top_k=5,
            min_version=None,
            max_version=None,
            json=False,
        )

        result = cli._cmd_query(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Test content" in captured.out

    def test_query_success_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        """Test successful query command with JSON output."""
        mock_kb_dir = tmp_path / "knowledge"
        articles_dir = mock_kb_dir / "articles"
        articles_dir.mkdir(parents=True)

        (articles_dir / "test.json").write_text(
            json.dumps({"entries": [{"body": "Test content about python"}]})
        )

        monkeypatch.setattr("claude_knowledge.query.KNOWLEDGE_DIR", mock_kb_dir)

        args = argparse.Namespace(
            question="python",
            top_k=5,
            min_version=None,
            max_version=None,
            json=True,
        )

        result = cli._cmd_query(args)

        assert result == 0
        captured = capsys.readouterr()
        results = json.loads(captured.out)
        assert isinstance(results, list)

    def test_query_no_results(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        """Test query with no matching results."""
        mock_kb_dir = tmp_path / "knowledge"
        articles_dir = mock_kb_dir / "articles"
        articles_dir.mkdir(parents=True)

        (articles_dir / "test.json").write_text(
            json.dumps({"entries": [{"body": "Completely unrelated content"}]})
        )

        monkeypatch.setattr("claude_knowledge.query.KNOWLEDGE_DIR", mock_kb_dir)

        args = argparse.Namespace(
            question="python",
            top_k=5,
            min_version=None,
            max_version=None,
            json=True,
        )

        result = cli._cmd_query(args)

        assert result == 0
        captured = capsys.readouterr()
        results = json.loads(captured.out)
        assert results == []


class TestCmdValidate:
    """Test _cmd_validate function."""

    def test_validate_success(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        """Test successful validate command."""
        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        (mock_kb_dir / "concepts").mkdir()
        (mock_kb_dir / "connections").mkdir()
        (mock_kb_dir / "qa").mkdir()
        (mock_kb_dir / "articles").mkdir()

        # Patch _config paths
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._config.REPORTS_DIR", tmp_path / "reports")
        monkeypatch.setattr("claude_knowledge._config.now_iso", lambda: "2024-01-15T10:00:00")
        # Patch _utils functions that validate.py uses
        monkeypatch.setattr("claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.list_wiki_articles", lambda: [])
        monkeypatch.setattr("claude_knowledge._utils.list_raw_files", lambda: [])
        monkeypatch.setattr("claude_knowledge._utils.load_state", lambda: {})

        # Import validate AFTER patching to get patched functions
        import claude_knowledge.validate as validate_mod
        # Also need to update cli module to use the re-imported validate
        import claude_knowledge.cli as cli_mod
        cli_mod.validate = validate_mod

        args = argparse.Namespace()

        result = cli_mod._cmd_validate(args)

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "issues" in output
        assert "report_path" in output

    def test_validate_with_errors(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        """Test validate command when there are errors."""
        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        concepts_dir = mock_kb_dir / "concepts"
        concepts_dir.mkdir()
        (mock_kb_dir / "connections").mkdir()
        (mock_kb_dir / "qa").mkdir()

        # Create an article with a broken link
        (concepts_dir / "article.md").write_text("""
# Article 1

See [[concepts/nonexistent]]
""")
        (concepts_dir / "orphan.md").write_text("""
# Orphan Article

No links to this.
""")

        # Patch _config paths
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._config.REPORTS_DIR", tmp_path / "reports")
        monkeypatch.setattr("claude_knowledge._config.now_iso", lambda: "2024-01-15T10:00:00")
        # Patch _utils functions - include some articles but trigger broken links and orphans
        monkeypatch.setattr("claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.list_wiki_articles", lambda: [
            concepts_dir / "article.md",
            concepts_dir / "orphan.md",
        ])
        monkeypatch.setattr("claude_knowledge._utils.list_raw_files", lambda: [])
        monkeypatch.setattr("claude_knowledge._utils.load_state", lambda: {})
        # Patch specific validation checks to trigger errors
        monkeypatch.setattr("claude_knowledge._utils.wiki_article_exists", lambda link: False)  # All links are broken
        monkeypatch.setattr("claude_knowledge._utils.count_inbound_links", lambda link, exclude=None: 0)  # All pages are orphans
        monkeypatch.setattr("claude_knowledge._utils.file_hash", lambda p: "abc123")

        args = argparse.Namespace()

        result = cli._cmd_validate(args)

        assert result == 1
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["issues"]["errors"] > 0


class TestMain:
    """Test main function."""

    def test_main_ingest_command(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test main with ingest command."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "test.md").write_text("# Test")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)

        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["claude-knowledge", "ingest", str(source_dir), "--dry-run"]):
            result = cli.main()
            assert result == 0

    def test_main_query_command(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test main with query command."""
        mock_kb_dir = tmp_path / "knowledge"
        articles_dir = mock_kb_dir / "articles"
        articles_dir.mkdir(parents=True)

        (articles_dir / "test.json").write_text(
            json.dumps({"entries": [{"body": "Test content"}]})
        )

        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)

        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["claude-knowledge", "query", "test", "--json"]):
            result = cli.main()
            assert result == 0

    def test_main_validate_command(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test main with validate command."""
        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        (mock_kb_dir / "concepts").mkdir()
        (mock_kb_dir / "connections").mkdir()
        (mock_kb_dir / "qa").mkdir()
        (mock_kb_dir / "articles").mkdir()

        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._config.REPORTS_DIR", tmp_path / "reports")
        monkeypatch.setattr("claude_knowledge._config.now_iso", lambda: "2024-01-15T10:00:00")
        # Patch _utils functions that validate.py uses
        monkeypatch.setattr("claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._utils.list_wiki_articles", lambda: [])
        monkeypatch.setattr("claude_knowledge._utils.list_raw_files", lambda: [])
        monkeypatch.setattr("claude_knowledge._utils.load_state", lambda: {})

        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["claude-knowledge", "validate"]):
            result = cli.main()
            assert result == 0

    def test_main_compile_command(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test main with compile command."""
        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()
        (daily_dir / "2024-01-15.md").write_text("2024-01-15T10:00:00 Test")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._config.DAILY_DIR", daily_dir)

        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["claude-knowledge", "compile", "--dry-run"]):
            result = cli.main()
            assert result == 0
