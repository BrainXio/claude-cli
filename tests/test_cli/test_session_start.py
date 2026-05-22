"""Tests for claude_cli.session_start."""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, "/home/mister-robot/workspace/claude-cli/src")


def test_get_recent_log_today():
    """Test get_recent_log with today's log."""
    from claude_cli.session_start import get_recent_log
    from claude_cli._config import DAILY_DIR

    today = datetime.now().strftime("%Y-%m-%d")
    log_path = DAILY_DIR / f"{today}.md"
    log_path.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")

    try:
        result = get_recent_log()
        # Should return last MAX_LOG_LINES (30) lines
        assert "Line 5" in result
    finally:
        log_path.unlink()


def test_get_recent_log_yesterday():
    """Test get_recent_log falls back to yesterday."""
    from claude_cli.session_start import get_recent_log
    from claude_cli._config import DAILY_DIR, now

    yesterday = (now() - timedelta(days=1)).strftime("%Y-%m-%d")
    log_path = DAILY_DIR / f"{yesterday}.md"
    log_path.write_text("Yesterday's log")

    try:
        result = get_recent_log()
        assert "Yesterday's log" in result
    finally:
        log_path.unlink()


def test_get_recent_log_no_log():
    """Test get_recent_log returns fallback message."""
    from claude_cli.session_start import get_recent_log
    from claude_cli._config import DAILY_DIR

    # Ensure no log exists for today or yesterday
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    today_path = DAILY_DIR / f"{today}.md"
    yesterday_path = DAILY_DIR / f"{yesterday}.md"

    if today_path.exists():
        today_path.unlink()
    if yesterday_path.exists():
        yesterday_path.unlink()

    result = get_recent_log()
    assert result == "(no recent daily log)"


def test_truncate_at_boundary_full_text():
    """Test _truncate_at_boundary with text shorter than max."""
    from claude_cli.session_start import _truncate_at_boundary

    text = "Short text"
    result = _truncate_at_boundary(text, 100)
    assert result == "Short text"


def test_truncate_at_boundary_with_boundary():
    """Test _truncate_at_boundary truncates at paragraph boundary."""
    from claude_cli.session_start import _truncate_at_boundary

    text = "First paragraph\n\nSecond paragraph\n\nThird paragraph"
    result = _truncate_at_boundary(text, 30)
    # Should truncate at the last double newline
    assert "..." in result
    assert "First paragraph" in result
    assert "Second paragraph" not in result


def test_truncate_at_boundary_no_boundary():
    """Test _truncate_at_boundary when no paragraph boundary found."""
    from claude_cli.session_start import _truncate_at_boundary

    text = "No boundary here just continuous text for truncation"
    result = _truncate_at_boundary(text, 20)
    assert "..." in result


def test_build_context_with_index():
    """Test build_context with existing index file."""
    from claude_cli.session_start import build_context
    from claude_cli._config import INDEX_FILE

    # Create mock index file
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text("# Knowledge Index\n\n- Item 1\n- Item 2")

    try:
        result = build_context()
        assert "Knowledge Base Index" in result
        assert "Knowledge Index" in result
    finally:
        INDEX_FILE.unlink()


def test_build_context_without_index():
    """Test build_context without index file."""
    from claude_cli.session_start import build_context
    from claude_cli._config import INDEX_FILE

    # Remove index file if exists
    if INDEX_FILE.exists():
        INDEX_FILE.unlink()

    result = build_context()
    assert "Knowledge Base Index" in result
    assert "(empty - run compile.py first)" in result


def test_main(capsys):
    """Test main() outputs JSON with context."""
    from claude_cli.session_start import main

    with patch("claude_cli.session_start.build_context") as mock_build:
        mock_build.return_value = "Test context"
        main()
        captured = capsys.readouterr()
        output = captured.out
        assert "SessionStart" in output
        assert "Test context" in output
