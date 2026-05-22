"""Tests for claude_knowledge._config."""

import warnings
from pathlib import Path

import pytest

from claude_knowledge import _config


class TestFindRootDir:
    """Test _find_root_dir function."""

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """PKB_ROOT env var takes highest priority."""
        monkeypatch.setenv("PKB_ROOT", str(tmp_path))
        result = _config._find_root_dir()
        assert result == tmp_path

    def test_sentinel_detection(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Detects project root via sentinel files."""
        # Override __file__ so the sentinel search starts from tmp_path
        import claude_knowledge._config as cfg
        original_file = cfg.__file__
        try:
            cfg.__file__ = str(tmp_path / "claude_knowledge" / "_config.py")
            (tmp_path / "pyproject.toml").write_text("[project]\n")
            result = cfg._find_root_dir()
            assert result == tmp_path
        finally:
            cfg.__file__ = original_file

    def test_fallback_warning(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Falls back with a warning when no sentinel found."""
        monkeypatch.delenv("PKB_ROOT", raising=False)
        import claude_knowledge._config as cfg
        original_file = cfg.__file__
        try:
            cfg.__file__ = str(tmp_path / "deep" / "claude_knowledge" / "_config.py")
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = cfg._find_root_dir()
                assert len(w) == 1
                assert "Could not detect project root" in str(w[0].message)
            assert "deep" in str(result)
        finally:
            cfg.__file__ = original_file


class TestDirectorySetters:
    """Test set_knowledge_dir and set_reports_dir."""

    def test_set_knowledge_dir(self, tmp_path: Path) -> None:
        """set_knowledge_dir updates all derived paths."""
        kb = tmp_path / "kb"
        _config.set_knowledge_dir(kb)
        assert _config.KNOWLEDGE_DIR == kb
        assert _config.CONCEPTS_DIR == kb / "concepts"
        assert _config.CONNECTIONS_DIR == kb / "connections"
        assert _config.QA_DIR == kb / "qa"

    def test_set_reports_dir(self, tmp_path: Path) -> None:
        """set_reports_dir updates all derived paths."""
        rep = tmp_path / "reports"
        _config.set_reports_dir(rep)
        assert _config.REPORTS_DIR == rep
        assert _config.REPORTS_STATE == rep / "state"
        assert _config.REPORTS_LOGS == rep / "logs"
        assert _config.REPORTS_TMP == rep / "tmp"


class TestEnsureDirs:
    """Test ensure_dirs function."""

    def test_creates_directories(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """ensure_dirs creates required directories."""
        monkeypatch.delenv("PKB_SKIP_ENSURE_DIRS", raising=False)
        monkeypatch.setattr(_config, "DAILY_DIR", tmp_path / "daily")
        monkeypatch.setattr(_config, "KNOWLEDGE_DIR", tmp_path / "kb")
        monkeypatch.setattr(_config, "CONCEPTS_DIR", tmp_path / "kb" / "concepts")
        monkeypatch.setattr(_config, "CONNECTIONS_DIR", tmp_path / "kb" / "connections")
        monkeypatch.setattr(_config, "QA_DIR", tmp_path / "kb" / "qa")
        monkeypatch.setattr(_config, "REPORTS_DIR", tmp_path / "reports")
        monkeypatch.setattr(_config, "REPORTS_LOGS", tmp_path / "reports" / "logs")
        monkeypatch.setattr(_config, "REPORTS_STATE", tmp_path / "reports" / "state")
        monkeypatch.setattr(_config, "REPORTS_TMP", tmp_path / "reports" / "tmp")

        _config.ensure_dirs()

        assert (tmp_path / "daily").exists()
        assert (tmp_path / "kb" / "concepts").exists()
        assert (tmp_path / "reports" / "logs").exists()

    def test_skipped_when_env_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ensure_dirs is a no-op when PKB_SKIP_ENSURE_DIRS=1."""
        monkeypatch.setenv("PKB_SKIP_ENSURE_DIRS", "1")
        # Should not raise even if directories are on a read-only path
        _config.ensure_dirs()


class TestTimeHelpers:
    """Test now, now_iso, today_iso."""

    def test_now_returns_datetime(self) -> None:
        """now() returns a datetime object."""
        result = _config.now()
        assert hasattr(result, "year")
        assert hasattr(result, "month")

    def test_today_iso_format(self) -> None:
        """today_iso returns YYYY-MM-DD format."""
        result = _config.today_iso()
        assert len(result) == 10
        assert result.count("-") == 2


class TestPrintConfigSummary:
    """Test print_config_summary function."""

    def test_prints_without_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """print_config_summary outputs lines without crashing."""
        _config.print_config_summary()
        captured = capsys.readouterr()
        assert "ROOT_DIR" in captured.out
        assert "AGENT_DIR" in captured.out
