"""Tests for claude_cli.check_model_vision."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, "/home/mister-robot/workspace/claude-cli/src")


def patch_file(content):
    """Helper to patch builtins.open with specific content."""
    mock_file = MagicMock()
    mock_file.__enter__.return_value.read.return_value = content
    return MagicMock(return_value=mock_file)


def test_get_active_model_with_ollama_cloud():
    """Test get_active_model with Ollama-Cloud format."""
    from claude_cli.check_model_vision import get_active_model

    state = {"mode": {"string": "Ollama-Cloud:deepseek-v4-pro:cloud"}}

    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", patch_file(json.dumps(state))):
            result = get_active_model()
            assert result == "deepseek-v4-pro:cloud"


def test_get_active_model_with_regular_format():
    """Test get_active_model with regular format."""
    from claude_cli.check_model_vision import get_active_model

    state = {"mode": {"string": "claude-3-5-sonnet"}}

    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", patch_file(json.dumps(state))):
            result = get_active_model()
            assert result == "claude-3-5-sonnet"


def test_get_active_model_missing_state_file():
    """Test get_active_model returns None when state file missing."""
    from claude_cli.check_model_vision import get_active_model

    with patch("os.path.exists", return_value=False):
        result = get_active_model()
        assert result is None


def test_get_active_model_missing_mode():
    """Test get_active_model returns None when mode is missing."""
    from claude_cli.check_model_vision import get_active_model

    state = {}

    with patch("os.path.exists", return_value=True):
        with patch("builtins.open") as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(state)
            mock_open.return_value.__enter__.return_value = mock_file
            result = get_active_model()
            assert result is None


def test_ollama_tags_success():
    """Test ollama_tags returns models from Ollama API."""
    from claude_cli.check_model_vision import ollama_tags

    mock_response = json.dumps(
        {
            "models": [
                {"name": "llama2", "size": "4.7GB"},
                {"name": "mistral", "size": "4.3GB"},
            ]
        }
    )

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response_obj = MagicMock()
        mock_response_obj.read.return_value = mock_response.encode()
        mock_response_obj.__enter__.return_value = mock_response_obj
        mock_response_obj.__exit__.return_value = None
        mock_urlopen.return_value.__enter__.return_value = mock_response_obj

        result = ollama_tags()
        assert len(result) == 2
        assert result[0]["name"] == "llama2"


def test_ollama_tags_error():
    """Test ollama_tags returns empty list on error."""
    from claude_cli.check_model_vision import ollama_tags

    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        result = ollama_tags()
        assert result == []


def test_has_vision_capability_true():
    """Test has_vision_capability detects vision capability."""
    from claude_cli.check_model_vision import has_vision_capability

    stdout = """
Capabilities
  vision
  text
"""
    result = has_vision_capability(stdout)
    assert result is True


def test_has_vision_capability_false():
    """Test has_vision_capability returns False without vision."""
    from claude_cli.check_model_vision import has_vision_capability

    stdout = """
Capabilities
  text
  reasoning
"""
    result = has_vision_capability(stdout)
    assert result is False


def test_has_vision_capability_no_caps_block():
    """Test has_vision_capability returns False when no Capabilities block."""
    from claude_cli.check_model_vision import has_vision_capability

    stdout = "No capabilities block here"
    result = has_vision_capability(stdout)
    assert result is False


def test_check_model_vision_with_ollama_show():
    """Test check_model_vision uses ollama show output."""
    from claude_cli.check_model_vision import check_model_vision

    with patch("claude_cli.check_model_vision.ollama_show") as mock_show:
        mock_show.return_value = ("Capabilities\n  vision", True)
        with patch(
            "claude_cli.check_model_vision.has_vision_capability"
        ) as mock_vision:
            mock_vision.return_value = True
            vision, matched = check_model_vision("llama3")
            assert vision is True
            assert matched == "llama3"


def test_check_model_vision_from_ollama_tags():
    """Test check_model_vision finds model in ollama tags."""
    from claude_cli.check_model_vision import check_model_vision

    with patch("claude_cli.check_model_vision.ollama_show") as mock_show:
        mock_show.side_effect = [
            ("Model not found", False),
            ("Capabilities\n  vision", True),
        ]
        with patch("claude_cli.check_model_vision.ollama_tags") as mock_tags:
            mock_tags.return_value = [{"name": "llama3", "remote_model": "llama3"}]
            with patch(
                "claude_cli.check_model_vision.has_vision_capability"
            ) as mock_vision:
                mock_vision.return_value = True
                vision, matched = check_model_vision("llama3")
                assert vision is True
                assert matched == "llama3"


def test_check_model_vision_known_remote():
    """Test check_model_vision matches known vision remote models."""
    from claude_cli.check_model_vision import check_model_vision

    with patch("claude_cli.check_model_vision.ollama_show") as mock_show:
        mock_show.return_value = ("", False)
        with patch("claude_cli.check_model_vision.ollama_tags") as mock_tags:
            mock_tags.return_value = [{"name": "qwen-vl", "remote_model": "qwen2.5-vl"}]
            vision, matched = check_model_vision("qwen2.5-vl")
            assert vision is True
            assert matched == "qwen-vl"


def test_main_empty_env_vars(capsys):
    """Test main() outputs JSON to stdout when no env vars are set."""
    from claude_cli.check_model_vision import main

    with patch.dict(os.environ, {}, clear=True):
        with patch("claude_cli.check_model_vision.get_active_model", return_value=None):
            main()
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert "models" in output
    assert "any_vision_available" in output
    assert output["any_vision_available"] is False


def test_main_with_env_var(capsys):
    """Test main() includes ANTHROPIC_DEFAULT_SONNET_MODEL in stdout."""
    from claude_cli.check_model_vision import main

    with patch.dict(
        os.environ, {"ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-3-5-sonnet"}
    ):
        with patch("claude_cli.check_model_vision.check_model_vision") as mock_check:
            mock_check.return_value = (None, None)
            main()
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert "ANTHROPIC_DEFAULT_SONNET_MODEL" in output["models"]


def test_main_active_model(capsys):
    """Test main() includes __active__ model in stdout when state exists."""
    from claude_cli.check_model_vision import main

    with patch.dict(os.environ, {}):
        with patch(
            "claude_cli.check_model_vision.get_active_model",
            return_value="granite-guardian:latest",
        ):
            with patch(
                "claude_cli.check_model_vision.check_model_vision"
            ) as mock_check:
                mock_check.return_value = (None, None)
                main()
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert "__active__" in output["models"]


def test_main_output_format(capsys):
    """Test main() stdout includes required fields."""
    from claude_cli.check_model_vision import main

    with patch.dict(os.environ, {}):
        with patch("claude_cli.check_model_vision.get_active_model", return_value=None):
            main()
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert "models" in output
    assert "any_vision_available" in output
    assert "checked_at" in output
