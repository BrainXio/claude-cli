"""Tests for claude_cli.pre_commit."""
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, "/home/mister-robot/workspace/claude-cli/src")


def _make_mocks(stdout: str = "", stderr: str = "", returncode: int = 0) -> MagicMock:
    m = MagicMock()
    m.stdout = stdout
    m.stderr = stderr
    m.returncode = returncode
    return m


def test_main_format_fixed(capsys: pytest.CaptureFixture) -> None:
    """Test main() detects and reports format fix."""
    from claude_cli.pre_commit import main

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            _make_mocks("reformatted 3 files"),
            _make_mocks(),
            _make_mocks(),
            _make_mocks(),
        ]
        rc = main()
        assert rc == 0
    captured = capsys.readouterr()
    assert "FIXED" in captured.out


def test_main_format_ok(capsys: pytest.CaptureFixture) -> None:
    """Test main() when format is already correct."""
    from claude_cli.pre_commit import main

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_make_mocks()] * 4
        rc = main()
        assert rc == 0
    captured = capsys.readouterr()
    assert "OK" in captured.out


def test_main_check_fixed(capsys: pytest.CaptureFixture) -> None:
    """Test main() detects and reports check fix."""
    from claude_cli.pre_commit import main

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            _make_mocks(),
            _make_mocks("fixed 2 issues"),
            _make_mocks(),
            _make_mocks(),
        ]
        rc = main()
        assert rc == 0
    captured = capsys.readouterr()
    assert "FIXED" in captured.out


def test_main_mypy_fail(capsys: pytest.CaptureFixture) -> None:
    """Test main() returns error on mypy failure."""
    from claude_cli.pre_commit import main

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            _make_mocks(),
            _make_mocks(),
            _make_mocks(),
            _make_mocks("error: Incompatible types", "TypeError", 1),
        ]
        rc = main()
        assert rc == 1
    captured = capsys.readouterr()
    assert "mypy: FAIL" in captured.out
    assert "Pre-commit blocked" in captured.out


def test_main_all_ok(capsys: pytest.CaptureFixture) -> None:
    """Test main() when all checks pass."""
    from claude_cli.pre_commit import main

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_make_mocks()] * 4
        rc = main()
        assert rc == 0
    captured = capsys.readouterr()
    assert "OK" in captured.out


def test_main_mypy_ok(capsys: pytest.CaptureFixture) -> None:
    """Test main() when mypy passes."""
    from claude_cli.pre_commit import main

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_make_mocks()] * 4
        rc = main()
        assert rc == 0
    captured = capsys.readouterr()
    assert "mypy: OK" in captured.out
