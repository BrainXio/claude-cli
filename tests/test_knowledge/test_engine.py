"""Tests for claude_knowledge.engine."""

from pathlib import Path

import pytest

from claude_knowledge import _utils, _config
from claude_knowledge.engine import run_pipeline


class TestRunPipeline:
    """Test run_pipeline function."""

    def test_empty_source(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test running pipeline on empty source directory."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        (mock_kb_dir / "concepts").mkdir()
        (mock_kb_dir / "connections").mkdir()
        (mock_kb_dir / "qa").mkdir()

        # Patch _config paths
        monkeypatch.setattr(_config, "KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr(_config, "DAILY_DIR", tmp_path / "daily")
        monkeypatch.setattr(_config, "REPORTS_DIR", tmp_path / "reports")
        monkeypatch.setattr(_config, "now_iso", lambda: "2024-01-15T10:00:00")
        # Patch _utils functions that validate.py uses
        monkeypatch.setattr(_utils, "get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr(_utils, "list_wiki_articles", lambda: [])
        monkeypatch.setattr(_utils, "list_raw_files", lambda: [])
        monkeypatch.setattr(_utils, "load_state", lambda: {})

        result = run_pipeline(source_dir)

        assert "prototypes_found" in result
        assert result["prototypes_found"] == 0
        assert "ingested" in result
        assert "unchanged" in result
        assert "errors" in result
        assert result["ingested"] == 0
        assert result["unchanged"] == 0
        assert result["errors"] == []
        assert "compiled" in result
        assert "issues" in result

    def test_pipeline_with_markdown_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test running pipeline with markdown files."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create markdown files
        (source_dir / "test1.md").write_text("# Test 1\n\nSome content")
        (source_dir / "test2.md").write_text("# Test 2\n\nMore content")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        (mock_kb_dir / "concepts").mkdir()
        (mock_kb_dir / "connections").mkdir()
        (mock_kb_dir / "qa").mkdir()

        # Patch _config paths
        monkeypatch.setattr(_config, "KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr(_config, "DAILY_DIR", tmp_path / "daily")
        monkeypatch.setattr(_config, "REPORTS_DIR", tmp_path / "reports")
        monkeypatch.setattr(_config, "now_iso", lambda: "2024-01-15T10:00:00")
        # Patch _utils functions that validate.py uses
        monkeypatch.setattr(_utils, "get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr(_utils, "list_wiki_articles", lambda: [])
        monkeypatch.setattr(_utils, "list_raw_files", lambda: [])
        monkeypatch.setattr(_utils, "load_state", lambda: {})

        result = run_pipeline(source_dir)

        assert result["ingested"] == 2
        assert "errors" in result

    def test_pipeline_dry_run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test running pipeline in dry-run mode."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "test.md").write_text("# Test")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        (mock_kb_dir / "concepts").mkdir()
        (mock_kb_dir / "connections").mkdir()
        (mock_kb_dir / "qa").mkdir()

        # Patch _utils functions
        monkeypatch.setattr(
            "claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir
        )
        monkeypatch.setattr("claude_knowledge._utils.list_wiki_articles", lambda: [])
        monkeypatch.setattr("claude_knowledge._utils.list_raw_files", lambda: [])
        monkeypatch.setattr("claude_knowledge._utils.load_state", lambda: {})
        monkeypatch.setattr(_config, "get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr(_config, "get_daily_dir", lambda: tmp_path / "daily")
        monkeypatch.setattr(
            "claude_knowledge.ingest.get_knowledge_dir", lambda: mock_kb_dir
        )
        monkeypatch.setattr(
            "claude_knowledge._config.REPORTS_DIR", tmp_path / "reports"
        )
        monkeypatch.setattr(
            "claude_knowledge._config.now_iso", lambda: "2024-01-15T10:00:00"
        )

        result = run_pipeline(source_dir, dry_run=True)

        assert result["ingested"] == 1
        assert "errors" in result

    def test_pipeline_force_all(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test running pipeline with force_all flag."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "test.md").write_text("# Test")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        (mock_kb_dir / "concepts").mkdir()
        (mock_kb_dir / "connections").mkdir()
        (mock_kb_dir / "qa").mkdir()

        # Patch _utils functions
        monkeypatch.setattr(
            "claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir
        )
        monkeypatch.setattr("claude_knowledge._utils.list_wiki_articles", lambda: [])
        monkeypatch.setattr("claude_knowledge._utils.list_raw_files", lambda: [])
        monkeypatch.setattr("claude_knowledge._utils.load_state", lambda: {})
        monkeypatch.setattr(_config, "get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr(_config, "get_daily_dir", lambda: tmp_path / "daily")
        monkeypatch.setattr(
            "claude_knowledge.ingest.get_knowledge_dir", lambda: mock_kb_dir
        )
        monkeypatch.setattr(
            "claude_knowledge._config.REPORTS_DIR", tmp_path / "reports"
        )
        monkeypatch.setattr(
            "claude_knowledge._config.now_iso", lambda: "2024-01-15T10:00:00"
        )

        # First run
        result1 = run_pipeline(source_dir)
        assert result1["ingested"] == 1

        # Second run without force_all
        result2 = run_pipeline(source_dir)
        assert result2["unchanged"] == 1

        # Third run with force_all
        result3 = run_pipeline(source_dir, force_all=True)
        assert result3["ingested"] == 1
        assert result3["unchanged"] == 0

    def test_pipeline_errors_handling(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that errors are captured in pipeline results."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "test.md").write_text("# Test")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        (mock_kb_dir / "concepts").mkdir()
        (mock_kb_dir / "connections").mkdir()
        (mock_kb_dir / "qa").mkdir()

        # Patch _utils functions
        monkeypatch.setattr(
            "claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir
        )
        monkeypatch.setattr("claude_knowledge._utils.list_wiki_articles", lambda: [])
        monkeypatch.setattr("claude_knowledge._utils.list_raw_files", lambda: [])
        monkeypatch.setattr("claude_knowledge._utils.load_state", lambda: {})
        monkeypatch.setattr(_config, "get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr(_config, "get_daily_dir", lambda: tmp_path / "daily")
        monkeypatch.setattr(
            "claude_knowledge.ingest.get_knowledge_dir", lambda: mock_kb_dir
        )
        monkeypatch.setattr(
            "claude_knowledge._config.REPORTS_DIR", tmp_path / "reports"
        )
        monkeypatch.setattr(
            "claude_knowledge._config.now_iso", lambda: "2024-01-15T10:00:00"
        )

        result = run_pipeline(source_dir)

        assert "errors" in result
        assert isinstance(result["errors"], list)

    def test_pipeline_validation_issues(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that validation issues are captured in pipeline results."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        (mock_kb_dir / "concepts").mkdir()
        (mock_kb_dir / "connections").mkdir()
        (mock_kb_dir / "qa").mkdir()

        # Patch _utils functions
        monkeypatch.setattr(
            "claude_knowledge._utils.get_knowledge_dir", lambda: mock_kb_dir
        )
        monkeypatch.setattr("claude_knowledge._utils.list_wiki_articles", lambda: [])
        monkeypatch.setattr("claude_knowledge._utils.list_raw_files", lambda: [])
        monkeypatch.setattr("claude_knowledge._utils.load_state", lambda: {})
        monkeypatch.setattr(_config, "get_knowledge_dir", lambda: mock_kb_dir)
        monkeypatch.setattr(_config, "get_daily_dir", lambda: tmp_path / "daily")
        monkeypatch.setattr(
            "claude_knowledge.ingest.get_knowledge_dir", lambda: mock_kb_dir
        )
        monkeypatch.setattr(
            "claude_knowledge._config.REPORTS_DIR", tmp_path / "reports"
        )
        monkeypatch.setattr(
            "claude_knowledge._config.now_iso", lambda: "2024-01-15T10:00:00"
        )

        result = run_pipeline(source_dir)

        assert "issues" in result
        assert "errors" in result["issues"]
        assert "warnings" in result["issues"]
        assert "suggestions" in result["issues"]
