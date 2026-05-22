"""Tests for claude_cli._utils."""
import sys
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, "/home/mister-robot/workspace/claude-cli/src")


def test_extract_conversation_context_basic():
    """Test extract_conversation_context with basic input."""
    from claude_cli._utils import extract_conversation_context
    transcript = Path("/tmp/test.jsonl")
    transcript.write_text(
        '{"message": {"role": "user", "content": "Hello"}}\n'
        '{"message": {"role": "assistant", "content": "Hi there"}}\n'
    )
    try:
        context, turn_count = extract_conversation_context(transcript)
        assert "Hello" in context
        assert "Hi there" in context
        assert turn_count == 2
    finally:
        transcript.unlink()


def test_extract_conversation_context_empty():
    """Test extract_conversation_context with empty file."""
    from claude_cli._utils import extract_conversation_context
    transcript = Path("/tmp/test.jsonl")
    transcript.write_text("")
    try:
        context, turn_count = extract_conversation_context(transcript)
        assert context == ""
        assert turn_count == 0
    finally:
        transcript.unlink()


def test_extract_conversation_context_invalid_lines():
    """Test extract_conversation_context with invalid JSON lines."""
    from claude_cli._utils import extract_conversation_context
    transcript = Path("/tmp/test.jsonl")
    transcript.write_text(
        "not valid json\n"
        '{"message": {"role": "user", "content": "Hello"}}\n'
        '{"invalid": "json"}\n'
    )
    try:
        context, turn_count = extract_conversation_context(transcript)
        assert "Hello" in context
        assert turn_count == 1
    finally:
        transcript.unlink()


def test_extract_conversation_context_filter_roles():
    """Test extract_conversation_context filters to user/assistant only."""
    from claude_cli._utils import extract_conversation_context
    transcript = Path("/tmp/test.jsonl")
    transcript.write_text(
        '{"message": {"role": "system", "content": "System message"}}\n'
        '{"message": {"role": "user", "content": "User message"}}\n'
        '{"message": {"role": "assistant", "content": "Assistant message"}}\n'
        '{"message": {"role": "tool", "content": "Tool message"}}\n'
    )
    try:
        context, turn_count = extract_conversation_context(transcript)
        assert "User message" in context
        assert "Assistant message" in context
        assert "System message" not in context
        assert "Tool message" not in context
        assert turn_count == 2
    finally:
        transcript.unlink()


def test_extract_conversation_context_list_content():
    """Test extract_conversation_context handles list content."""
    from claude_cli._utils import extract_conversation_context
    transcript = Path("/tmp/test.jsonl")
    transcript.write_text(
        '{"message": {"role": "user", "content": [{"type": "text", "text": "Hello"}]}}\n'
    )
    try:
        context, turn_count = extract_conversation_context(transcript)
        assert "Hello" in context
        assert turn_count == 1
    finally:
        transcript.unlink()


def test_extract_conversation_context_max_turns():
    """Test extract_conversation_context respects max_turns."""
    from claude_cli._utils import extract_conversation_context
    transcript = Path("/tmp/test.jsonl")
    transcript.write_text(
        '{"message": {"role": "user", "content": "Turn 1"}}\n'
        '{"message": {"role": "assistant", "content": "Turn 2"}}\n'
        '{"message": {"role": "user", "content": "Turn 3"}}\n'
        '{"message": {"role": "assistant", "content": "Turn 4"}}\n'
        '{"message": {"role": "user", "content": "Turn 5"}}\n'
    )
    try:
        context, turn_count = extract_conversation_context(transcript, max_turns=3)
        assert "Turn 3" in context
        assert "Turn 2" not in context
        assert turn_count == 3
    finally:
        transcript.unlink()


def test_extract_conversation_context_max_chars():
    """Test extract_conversation_context respects max_chars."""
    from claude_cli._utils import extract_conversation_context
    transcript = Path("/tmp/test.jsonl")
    long_content = "a" * 1000
    transcript.write_text(
        f'{{"message": {{"role": "user", "content": "{long_content}"}}}}\n'
        '{"message": {"role": "assistant", "content": "Short"}}\n'
    )
    try:
        context, turn_count = extract_conversation_context(transcript, max_chars=500)
        assert len(context) <= 500
        assert turn_count == 2
    finally:
        transcript.unlink()


def test_parse_stdin_json_success():
    """Test parse_stdin_json with valid JSON."""
    from claude_cli._utils import parse_stdin_json
    test_data = {"key": "value", "number": 42}
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = json.dumps(test_data)
        result = parse_stdin_json()
        assert result == test_data


def test_parse_stdin_json_empty():
    """Test parse_stdin_json with empty string."""
    from claude_cli._utils import parse_stdin_json
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = ""
        result = parse_stdin_json()
        assert result is None


def test_parse_stdin_json_invalid():
    """Test parse_stdin_json with invalid JSON."""
    from claude_cli._utils import parse_stdin_json
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = "not valid json"
        result = parse_stdin_json()
        assert result is None


def test_parse_stdin_json_whitespace():
    """Test parse_stdin_json with whitespace only."""
    from claude_cli._utils import parse_stdin_json
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = "   "
        result = parse_stdin_json()
        assert result is None


def test_spawn_detached_linux():
    """Test spawn_detached with Linux platform."""
    from claude_cli._utils import spawn_detached
    with patch("subprocess.Popen") as mock_popen:
        with patch("sys.platform", "linux"):
            spawn_detached(["echo", "test"], cwd="/tmp")
            mock_popen.assert_called_once()
            kwargs = mock_popen.call_args[1]
            assert kwargs["start_new_session"] is True


def test_spawn_detached_with_log_path():
    """Test spawn_detached with log path."""
    from claude_cli._utils import spawn_detached
    log_path = Path("/tmp/test.log")
    with patch("builtins.open") as mock_open:
        with patch("subprocess.Popen") as mock_popen:
            spawn_detached(["echo", "test"], log_path=log_path, cwd="/tmp")
            mock_open.assert_called_once()
            mock_popen.assert_called_once()
