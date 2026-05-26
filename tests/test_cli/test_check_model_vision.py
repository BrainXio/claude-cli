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


class FakeProvider:
    """Fake LLM provider for testing check_model_vision."""

    def __init__(self, models=None, show_map=None):
        self._models = models or []
        self._show_map = show_map or {}

    def list_models(self):
        return self._models

    def show_model(self, model_name):
        return self._show_map.get(model_name, ("", False))


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


def test_ollama_provider_list_models_success():
    """Test OllamaProvider.list_models returns models from API."""
    from claude_cli.check_model_vision import OllamaProvider

    mock_response = json.dumps(
        {
            "models": [
                {"name": "llama2", "size": "4.7GB"},
                {"name": "mistral", "size": "4.3GB"},
            ]
        }
    )

    with patch(
        "claude_cli.check_model_vision.fetch_with_backoff",
        return_value=mock_response.encode(),
    ):
        provider = OllamaProvider()
        result = provider.list_models()
        assert len(result) == 2
        assert result[0]["name"] == "llama2"


def test_ollama_provider_list_models_error():
    """Test OllamaProvider.list_models returns empty list on error."""
    from claude_cli.check_model_vision import OllamaProvider

    with patch(
        "claude_cli.check_model_vision.fetch_with_backoff",
        side_effect=Exception("Network error"),
    ):
        provider = OllamaProvider()
        result = provider.list_models()
        assert result == []


def test_ollama_provider_show_model_success():
    """Test OllamaProvider.show_model returns stdout."""
    from claude_cli.check_model_vision import OllamaProvider

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "Capabilities\n  vision"
        mock_run.return_value.returncode = 0
        provider = OllamaProvider()
        stdout, ok = provider.show_model("llama3")
        assert ok is True
        assert "vision" in stdout


def test_ollama_provider_show_model_failure():
    """Test OllamaProvider.show_model returns failure."""
    from claude_cli.check_model_vision import OllamaProvider

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = ""
        mock_run.return_value.returncode = 1
        provider = OllamaProvider()
        stdout, ok = provider.show_model("unknown")
        assert ok is False
        assert stdout == ""


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


def test_check_model_vision_with_show():
    """Test check_model_vision uses provider.show_model."""
    from claude_cli.check_model_vision import check_model_vision

    provider = FakeProvider(show_map={"llama3": ("Capabilities\n  vision", True)})
    vision, matched = check_model_vision("llama3", provider)
    assert vision is True
    assert matched == "llama3"


def test_check_model_vision_from_list_models():
    """Test check_model_vision finds model via provider.list_models."""
    from claude_cli.check_model_vision import check_model_vision

    provider = FakeProvider(
        models=[{"name": "llama3", "remote_model": "llama3"}],
        show_map={
            "llama3": ("Capabilities\n  vision", True),
        },
    )
    vision, matched = check_model_vision("llama3", provider)
    assert vision is True
    assert matched == "llama3"


def test_check_model_vision_known_remote():
    """Test check_model_vision matches known vision remote models."""
    from claude_cli.check_model_vision import check_model_vision

    provider = FakeProvider(
        models=[{"name": "qwen-vl", "remote_model": "qwen2.5-vl"}],
        show_map={"qwen2.5-vl": ("", False)},
    )
    vision, matched = check_model_vision("qwen2.5-vl", provider)
    assert vision is True
    assert matched == "qwen-vl"


def test_check_model_vision_none():
    """Test check_model_vision returns None for None input."""
    from claude_cli.check_model_vision import check_model_vision

    provider = FakeProvider()
    vision, matched = check_model_vision(None, provider)
    assert vision is None
    assert matched is None


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
