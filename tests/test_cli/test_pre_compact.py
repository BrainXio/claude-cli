"""Tests for claude_cli.pre_compact."""

import os
import sys
from unittest.mock import patch

os.environ["PKB_SKIP_ENSURE_DIRS"] = "1"

sys.path.insert(0, "/home/mister-robot/workspace/claude-cli/src")


def test_main_no_stdin():
    """Test main() when stdin parsing fails."""
    from claude_cli.pre_compact import main

    with patch("claude_cli.pre_compact.parse_stdin_json", return_value=None):
        # Function should return early without logging when stdin parsing fails
        result = main()
        assert result is None


def test_main_no_transcript_path():
    """Test main() when no transcript path is provided."""
    from claude_cli.pre_compact import main

    with patch(
        "claude_cli.pre_compact.parse_stdin_json",
        return_value={"session_id": "test-session", "transcript_path": ""},
    ):
        main()


def test_main_invalid_transcript_path():
    """Test main() when transcript path is not a string."""
    from claude_cli.pre_compact import main

    with patch(
        "claude_cli.pre_compact.parse_stdin_json",
        return_value={"session_id": "test-session", "transcript_path": 12345},
    ):
        main()


def test_main_session_id_not_string():
    """Test main() when session_id is not a string."""
    from claude_cli.pre_compact import main

    with patch(
        "claude_cli.pre_compact.parse_stdin_json",
        return_value={"session_id": 12345, "transcript_path": "/tmp/test.jsonl"},
    ):
        main()


def test_main_transcript_not_exists():
    """Test main() when transcript file doesn't exist."""
    from claude_cli.pre_compact import main

    with patch(
        "claude_cli.pre_compact.parse_stdin_json",
        return_value={
            "session_id": "test-session",
            "transcript_path": "/nonexistent/path.jsonl",
        },
    ):
        main()


def test_main_empty_context():
    """Test main() when context extraction returns empty."""
    from claude_cli.pre_compact import main

    with patch(
        "claude_cli.pre_compact.parse_stdin_json",
        return_value={
            "session_id": "test-session",
            "transcript_path": "/tmp/test.jsonl",
        },
    ):
        with patch(
            "claude_cli.pre_compact.extract_conversation_context"
        ) as mock_extract:
            mock_extract.return_value = ("", 10)
            main()


def test_main_few_turns():
    """Test main() when context has too few turns."""
    from claude_cli.pre_compact import main

    with patch(
        "claude_cli.pre_compact.parse_stdin_json",
        return_value={
            "session_id": "test-session",
            "transcript_path": "/tmp/test.jsonl",
        },
    ):
        with patch(
            "claude_cli.pre_compact.extract_conversation_context"
        ) as mock_extract:
            mock_extract.return_value = ("Some context", 3)
            main()


def test_main_success(tmp_path):
    """Test main() with successful execution."""
    from claude_cli.pre_compact import main

    # Create transcript file with proper JSONL format
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text('{"message": {"role": "user", "content": "Hello"}}\n')

    # Create ROOT_DIR structure
    root_dir = tmp_path / ".claude"
    tmp_dir = root_dir / "reports" / "tmp"
    tmp_dir.mkdir(parents=True)

    with patch(
        "claude_cli.pre_compact.parse_stdin_json",
        return_value={"session_id": "test-session", "transcript_path": str(transcript)},
    ):
        with patch("claude_cli.pre_compact.ROOT_DIR", root_dir):
            with patch(
                "claude_cli.pre_compact.extract_conversation_context"
            ) as mock_extract:
                # Return enough turns to pass MIN_TURNS_TO_FLUSH (5)
                mock_extract.return_value = ("User: Hello\n", 5)
                with patch("claude_cli.pre_compact.spawn_detached") as mock_spawn:
                    main()
                    assert mock_spawn.called


def test_main_with_exception():
    """Test main() handles exception during context extraction."""
    from claude_cli.pre_compact import main

    with patch(
        "claude_cli.pre_compact.parse_stdin_json",
        return_value={
            "session_id": "test-session",
            "transcript_path": "/tmp/test.jsonl",
        },
    ):
        with patch(
            "claude_cli.pre_compact.extract_conversation_context",
            side_effect=Exception("Test error"),
        ):
            main()


def test_main_context_written(tmp_path):
    """Test main() writes context file to tmp directory."""
    from claude_cli.pre_compact import main

    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text('{"message": {"role": "user", "content": "Hello"}}\n')

    root_dir = tmp_path / ".claude"
    tmp_dir = root_dir / "reports" / "tmp"
    tmp_dir.mkdir(parents=True)

    with patch(
        "claude_cli.pre_compact.parse_stdin_json",
        return_value={"session_id": "test-session", "transcript_path": str(transcript)},
    ):
        with patch("claude_cli.pre_compact.ROOT_DIR", root_dir):
            with patch(
                "claude_cli.pre_compact.extract_conversation_context"
            ) as mock_extract:
                # Return enough turns to pass MIN_TURNS_TO_FLUSH (5)
                mock_extract.return_value = ("User: Hello\n", 5)
                with patch("claude_cli.pre_compact.spawn_detached") as mock_spawn:
                    main()
                    assert mock_spawn.called
                    call_args = mock_spawn.call_args[0][0]
                    assert "uv" in call_args
                    assert "python" in call_args
