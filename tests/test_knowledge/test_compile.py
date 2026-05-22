"""Tests for claude_knowledge.compile."""

import pytest
from pathlib import Path
import json
import shutil

from claude_knowledge.compile import _extract_entries, compile_logs


class TestExtractEntries:
    """Test _extract_entries function."""

    def test_empty_content(self) -> None:
        """Test empty log content."""
        entries = _extract_entries("")
        assert entries == []

    def test_single_entry(self) -> None:
        """Test single timestamped entry."""
        content = "2024-01-15T10:30:00 Some work done"
        entries = _extract_entries(content)
        assert len(entries) == 1
        assert entries[0]["timestamp"] == "2024-01-15T10:30:00"
        assert entries[0]["body"] == "2024-01-15T10:30:00 Some work done"
        assert entries[0]["tags"] == []

    def test_multiple_entries(self) -> None:
        """Test multiple timestamped entries."""
        content = """2024-01-15T10:30:00 Morning standup
2024-01-15T14:00:00 Afternoon work session"""
        entries = _extract_entries(content)
        assert len(entries) == 2
        assert entries[0]["body"].startswith("2024-01-15T10:30:00")
        assert entries[1]["body"].startswith("2024-01-15T14:00:00")

    def test_tags_extraction(self) -> None:
        """Test tag extraction from entries."""
        content = "2024-01-15T10:30:00 Meeting #standup #team"
        entries = _extract_entries(content)
        assert entries[0]["tags"] == ["standup", "team"]

    def test_content_appended_to_body(self) -> None:
        """Test that non-timestamped lines append to current entry."""
        content = """2024-01-15T10:30:00 First line
Continuation of first entry
2024-01-15T11:00:00 Second entry"""
        entries = _extract_entries(content)
        assert len(entries) == 2
        assert "Continuation of first entry" in entries[0]["body"]
        assert "First line" in entries[0]["body"]

    def test_blank_lines_ignored(self) -> None:
        """Test that blank lines don't create entries."""
        content = """2024-01-15T10:30:00 Entry one

2024-01-15T11:00:00 Entry two

Some trailing content"""
        entries = _extract_entries(content)
        assert len(entries) == 2


class TestCompileLogs:
    """Test compile_logs function."""

    def test_basic_compilation(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test basic daily log compilation."""
        # Create daily directory with a log file
        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()
        (daily_dir / "2024-01-15.md").write_text("""2024-01-15T10:00:00 Morning session
#standup #planning

2024-01-15T14:00:00 Afternoon work
#development
""")

        # Mock KNOWLEDGE_DIR
        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._config.DAILY_DIR", daily_dir)

        result = compile_logs(dry_run=True)

        assert result["compiled"] == 1
        assert result["errors"] == []

        # Verify articles directory exists
        articles_dir = mock_kb_dir / "articles"
        assert articles_dir.exists()

    def test_compilation_creates_article(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that compilation creates article file."""
        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()
        (daily_dir / "2024-01-15.md").write_text("2024-01-15T10:00:00 Test entry")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._config.DAILY_DIR", daily_dir)

        result = compile_logs()

        assert result["compiled"] == 1

        article_file = mock_kb_dir / "articles" / "2024-01-15.json"
        assert article_file.exists()

        data = json.loads(article_file.read_text())
        assert data["date"] == "2024-01-15"
        assert len(data["entries"]) == 1
        assert "compiled_at" in data

    def test_empty_daily_log_ignored(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that empty daily logs are ignored."""
        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()
        (daily_dir / "2024-01-15.md").write_text("")
        (daily_dir / "2024-01-16.md").write_text("2024-01-16T10:00:00 Valid log")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._config.DAILY_DIR", daily_dir)

        result = compile_logs()

        assert result["compiled"] == 1

    def test_multiple_daily_logs(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test compilation of multiple daily logs."""
        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()
        (daily_dir / "2024-01-15.md").write_text("2024-01-15T10:00:00 Entry")
        (daily_dir / "2024-01-16.md").write_text("2024-01-16T10:00:00 Entry")
        (daily_dir / "2024-01-17.md").write_text("2024-01-17T10:00:00 Entry")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._config.DAILY_DIR", daily_dir)

        result = compile_logs()

        assert result["compiled"] == 3

    def test_state_persistence(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that compile state is persisted."""
        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()
        (daily_dir / "2024-01-15.md").write_text("2024-01-15T10:00:00 Entry")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._config.DAILY_DIR", daily_dir)

        compile_logs()

        state_file = mock_kb_dir / "compile_state.json"
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert "2024-01-15" in state

    def test_dry_run_no_state_write(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that dry_run doesn't write state file."""
        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()
        (daily_dir / "2024-01-15.md").write_text("2024-01-15T10:00:00 Entry")

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._config.DAILY_DIR", daily_dir)

        result = compile_logs(dry_run=True)

        assert result["compiled"] == 1
        state_file = mock_kb_dir / "compile_state.json"
        assert not state_file.exists()

    def test_no_daily_logs(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test when no daily logs exist."""
        daily_dir = tmp_path / "daily"
        daily_dir.mkdir()

        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)
        monkeypatch.setattr("claude_knowledge._config.DAILY_DIR", daily_dir)

        result = compile_logs()

        assert result["compiled"] == 0
        assert result["errors"] == []
