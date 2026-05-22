"""Tests for claude_cli.bootstrap."""
import os
import sys
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, "/home/mister-robot/workspace/claude-cli/src")


def test_find_git_root_success():
    """Test _find_git_root returns git root when in repo."""
    from claude_cli.bootstrap import _find_git_root
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "/home/test/repo\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        result = _find_git_root()
        assert result == Path("/home/test/repo")


def test_find_git_root_timeout():
    """Test _find_git_root returns None on timeout."""
    from claude_cli.bootstrap import _find_git_root
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("git", 5)
        result = _find_git_root()
        assert result is None


def test_find_git_root_subprocess_error():
    """Test _find_git_root returns None on subprocess error."""
    from claude_cli.bootstrap import _find_git_root
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.SubprocessError("error")
        result = _find_git_root()
        assert result is None


def test_find_git_root_not_in_repo():
    """Test _find_git_root returns None when not in a repo."""
    from claude_cli.bootstrap import _find_git_root
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "not a git repository"
        mock_run.return_value = mock_result
        result = _find_git_root()
        assert result is None


def test_sweep_temp_files_success(tmp_path):
    """Test _sweep_temp_files removes old temp files."""
    from claude_cli.bootstrap import _sweep_temp_files
    from claude_cli._config import REPORTS_TMP
    import time
    # Override REPORTS_TMP to use tmp_path
    with patch("claude_cli.bootstrap.REPORTS_TMP", tmp_path):
        # Create a temp file
        old_file = tmp_path / "session-flush-test-123.md"
        old_file.write_text("test content")
        # Set mtime to 48 hours ago
        old_time = time.time() - (48 * 3600)
        os.utime(old_file, (old_time, old_time))
        _sweep_temp_files(max_age_hours=24)
        assert not old_file.exists()


def test_sweep_temp_files_no_files(tmp_path):
    """Test _sweep_temp_files when no temp files exist."""
    from claude_cli.bootstrap import _sweep_temp_files
    with patch("claude_cli.bootstrap.REPORTS_TMP", tmp_path):
        _sweep_temp_files()


def test_sweep_temp_files_not_old_enough(tmp_path):
    """Test _sweep_temp_files doesn't remove recent files."""
    from claude_cli.bootstrap import _sweep_temp_files
    from claude_cli._config import REPORTS_TMP
    import time
    with patch("claude_cli.bootstrap.REPORTS_TMP", tmp_path):
        recent_file = tmp_path / "session-flush-recent.md"
        recent_file.write_text("test content")
        _sweep_temp_files(max_age_hours=24)
        assert recent_file.exists()


def test_main_no_stdin():
    """Test main() when stdin parsing fails."""
    from claude_cli._identity import register_bootstrap_session
    from claude_cli.bootstrap import main

    with patch("claude_cli._identity.register_bootstrap_session") as mock_register:
        with patch.dict(os.environ, {"CLAUDE_AGENT_NAME": "test"}):
            mock_register.return_value = {
                "agent_id": "w.test",
                "session_id": "w.test.20240515.x7k2",
                "started_at": "2024-01-01T00:00:00+00:00",
            }
            result = main()
            mock_register.assert_called_once()


def test_main_batch_mode():
    """Test main() with batch mode enabled."""
    from claude_cli._identity import register_bootstrap_session, mark_batch_executed
    from claude_cli.bootstrap import main

    with patch("claude_cli._identity.register_bootstrap_session") as mock_register:
        with patch("claude_cli._identity.mark_batch_executed") as mock_mark:
            with patch.dict(os.environ, {"CLAUDE_AGENT_NAME": "test", "CLAUDE_BATCH_ID": "batch-123"}):
                mock_register.return_value = {
                    "agent_id": "w.test",
                    "session_id": "w.test.20240515.x7k2",
                    "started_at": "2024-01-01T00:00:00+00:00",
                }
                result = main()
                mock_mark.assert_called_once()
