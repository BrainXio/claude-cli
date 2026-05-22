"""Tests for claude_cli.statusline."""

import sys
import json
from unittest.mock import patch

sys.path.insert(0, "/home/mister-robot/workspace/claude-cli/src")


def test_build_bar_full():
    """Test build_bar with 100%."""
    from claude_cli.statusline import build_bar

    bar = build_bar(100, width=10)
    assert bar == "##########"


def test_build_bar_empty():
    """Test build_bar with 0%."""
    from claude_cli.statusline import build_bar

    bar = build_bar(0, width=10)
    assert bar == "----------"


def test_build_bar_half():
    """Test build_bar with 50%."""
    from claude_cli.statusline import build_bar

    bar = build_bar(50, width=10)
    assert bar == "#####-----"


def test_color_for_usage_green():
    """Test color_for_usage returns green for low usage."""
    from claude_cli.statusline import color_for_usage

    assert color_for_usage(30) == "\033[32m"


def test_color_for_usage_yellow():
    """Test color_for_usage returns yellow for medium usage."""
    from claude_cli.statusline import color_for_usage

    assert color_for_usage(60) == "\033[33m"


def test_color_for_usage_orange():
    """Test color_for_usage returns orange for high usage."""
    from claude_cli.statusline import color_for_usage

    assert color_for_usage(85) == "\033[38;5;208m"


def test_color_for_usage_red():
    """Test color_for_usage returns red for very high usage."""
    from claude_cli.statusline import color_for_usage

    assert color_for_usage(95) == "\033[31m"


def test_main_valid_input_with_usage(capsys):
    """Test main() with valid JSON containing usage."""
    from claude_cli.statusline import main

    input_data = {
        "model": {"display_name": "claude-3-5-sonnet"},
        "context_window": {"used_percentage": 75},
    }
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = json.dumps(input_data)
        main()
    captured = capsys.readouterr()
    assert "claude-3-5-sonnet" in captured.out
    assert "%" in captured.out


def test_main_valid_input_no_usage(capsys):
    """Test main() with valid JSON but no usage."""
    from claude_cli.statusline import main

    input_data = {"model": {"display_name": "claude-3-5-sonnet"}}
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = json.dumps(input_data)
        main()
    captured = capsys.readouterr()
    assert "claude-3-5-sonnet" in captured.out
    assert "%" not in captured.out


def test_main_invalid_json(capsys):
    """Test main() with invalid JSON."""
    from claude_cli.statusline import main

    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = "not valid json"
        main()


def test_main_empty_input(capsys):
    """Test main() with empty input."""
    from claude_cli.statusline import main

    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = ""
        main()


def test_main_missing_model(capsys):
    """Test main() with missing model field."""
    from claude_cli.statusline import main

    input_data = {"context_window": {"used_percentage": 50}}
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = json.dumps(input_data)
        main()
    captured = capsys.readouterr()
    assert "unknown" in captured.out


def test_main_missing_context_window(capsys):
    """Test main() with missing context_window field."""
    from claude_cli.statusline import main

    input_data = {"model": {"display_name": "claude-3-5-sonnet"}}
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = json.dumps(input_data)
        main()
    captured = capsys.readouterr()
    assert "claude-3-5-sonnet" in captured.out


def test_main_ansi_codes_preserved(capsys):
    """Test that ANSI color codes are preserved in output."""
    from claude_cli.statusline import main

    input_data = {
        "model": {"display_name": "test-model"},
        "context_window": {"used_percentage": 95},
    }
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = json.dumps(input_data)
        main()
    captured = capsys.readouterr()
    assert "\033[31m" in captured.out  # red for high usage
    assert "\033[00m" in captured.out  # reset
