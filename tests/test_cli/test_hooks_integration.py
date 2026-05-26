"""Integration tests for claude_cli hooks.

Tests hook main() entry points with mocked external dependencies.
Identity layer internals are out of scope — mocked at module level.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, "/home/mister-robot/workspace/claude-cli/src")


class TestBootstrapHook:
    """Integration tests for bootstrap main()."""

    def test_bootstrap_writes_state(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """bootstrap writes state.json with correct structure."""
        monkeypatch.setattr("claude_cli.bootstrap.DATA_DIR", tmp_path / "data")
        monkeypatch.setattr("claude_cli.bootstrap.STATE_FILE", tmp_path / "data" / "state.json")
        monkeypatch.setattr("claude_cli.bootstrap.REPORTS_LOGS", tmp_path / "reports" / "logs")
        monkeypatch.setattr("claude_cli.bootstrap.REPORTS_STATE", tmp_path / "reports" / "state")
        monkeypatch.setattr("claude_cli.bootstrap.REPORTS_TMP", tmp_path / "reports" / "tmp")

        mock_record = {
            "agent_id": "test-agent",
            "session_id": "sess-123",
            "work_items": [],
            "work_queue": [],
        }

        with patch("claude_cli._bootstrap_identity.register_and_resume", return_value=(mock_record, [], 0)):
            with patch("claude_cli.bootstrap._ensure_guardian"):
                with patch("claude_cli.bootstrap._sweep_temp_files"):
                    with patch("claude_cli.bootstrap._sync_docs"):
                        from claude_cli.bootstrap import main

                        main()

        state_file = tmp_path / "data" / "state.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["agent_id"] == "test-agent"
        assert data["session_id"] == "sess-123"
        assert data["version"] == 1
        assert "bootstrapped_at" in data["meta"]

    def test_bootstrap_creates_directories(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """bootstrap creates required data directories."""
        monkeypatch.setattr("claude_cli.bootstrap.DATA_DIR", tmp_path / "data")
        monkeypatch.setattr("claude_cli.bootstrap.STATE_FILE", tmp_path / "data" / "state.json")
        monkeypatch.setattr("claude_cli.bootstrap.REPORTS_LOGS", tmp_path / "reports" / "logs")
        monkeypatch.setattr("claude_cli.bootstrap.REPORTS_STATE", tmp_path / "reports" / "state")
        monkeypatch.setattr("claude_cli.bootstrap.REPORTS_TMP", tmp_path / "reports" / "tmp")

        mock_record = {
            "agent_id": "a",
            "session_id": "s",
            "work_items": [],
            "work_queue": [],
        }

        with patch("claude_cli._bootstrap_identity.register_and_resume", return_value=(mock_record, [], 0)):
            with patch("claude_cli.bootstrap._ensure_guardian"):
                with patch("claude_cli.bootstrap._sweep_temp_files"):
                    with patch("claude_cli.bootstrap._sync_docs"):
                        from claude_cli.bootstrap import main

                        main()

        assert (tmp_path / "data" / "daily").exists()
        assert (tmp_path / "reports" / "logs").exists()
        assert (tmp_path / "reports" / "tmp").exists()


class TestSessionEndHook:
    """Integration tests for session_end main()."""

    def test_session_end_with_transcript(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """session_end reads transcript and spawns flush when context is non-empty."""
        monkeypatch.setattr("claude_cli._config.REPORTS_LOGS", tmp_path / "logs")
        monkeypatch.setattr("claude_cli._config.REPORTS_TMP", tmp_path / "tmp")

        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(
            json.dumps({"role": "user", "content": "hello"}) + "\n"
            + json.dumps({"role": "assistant", "content": "hi"}) + "\n"
        )

        hook_input = {"session_id": "sess-abc", "transcript_path": str(transcript)}

        spawned_cmds: list[list[str]] = []

        def fake_spawn(cmd: list[str], cwd: str | None = None) -> None:
            spawned_cmds.append(cmd)

        monkeypatch.setattr("claude_cli.session_end.spawn_detached", fake_spawn)

        from claude_cli.session_end import main

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = json.dumps(hook_input)
            main()

        assert len(spawned_cmds) == 1
        assert any("flush.py" in str(arg) for arg in spawned_cmds[0])

    def test_session_end_empty_transcript(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """session_end skips flush when transcript is empty."""
        monkeypatch.setattr("claude_cli._config.REPORTS_LOGS", tmp_path / "logs")
        monkeypatch.setattr("claude_cli._config.REPORTS_TMP", tmp_path / "tmp")

        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text("")

        hook_input = {"session_id": "sess-xyz", "transcript_path": str(transcript)}

        spawned_cmds: list[list[str]] = []
        monkeypatch.setattr("claude_cli.session_end.spawn_detached", lambda cmd, cwd=None: spawned_cmds.append(cmd))

        from claude_cli.session_end import main

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = json.dumps(hook_input)
            main()

        assert len(spawned_cmds) == 0

    def test_session_end_no_stdin(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """session_end returns early when no stdin."""
        monkeypatch.setattr("claude_cli._config.REPORTS_LOGS", tmp_path / "logs")
        monkeypatch.setattr("claude_cli._config.REPORTS_TMP", tmp_path / "tmp")

        from claude_cli.session_end import main

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = ""
            rc = main()
        assert rc is None


class TestStandardsGuardHook:
    """Integration tests for standards_guard main()."""

    def test_guard_blocks_philosophy_sludge(self, capsys: pytest.CaptureFixture) -> None:
        """standards_guard denies Edit with forbidden philosophy content."""
        from claude_cli.standards_guard import main

        payload = {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": ".github/README.md",
                "new_string": "This is a quiet joy system.",
            },
        }

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = json.dumps(payload)
            main()

        captured = capsys.readouterr()
        assert "deny" in captured.out
        assert "quiet joy" in captured.out

    def test_guard_allows_safe_content(self, capsys: pytest.CaptureFixture) -> None:
        """standards_guard allows safe edits."""
        from claude_cli.standards_guard import main

        payload = {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": ".github/README.md",
                "new_string": "Standard documentation content.",
            },
        }

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = json.dumps(payload)
            main()

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_guard_blocks_manifesto_tone(self, capsys: pytest.CaptureFixture) -> None:
        """standards_guard denies manifesto tone in standards docs."""
        from claude_cli.standards_guard import main

        payload = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "CONTRIBUTING.md",
                "content": "This workflow is the only allowed process.",
            },
        }

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = json.dumps(payload)
            main()

        captured = capsys.readouterr()
        assert "deny" in captured.out
        assert "manifesto tone" in captured.out

    def test_guard_ignores_non_guarded_files(self, capsys: pytest.CaptureFixture) -> None:
        """standards_guard allows non-standards files without checking."""
        from claude_cli.standards_guard import main

        payload = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "src/main.py",
                "content": "This is a quiet joy system.",
            },
        }

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = json.dumps(payload)
            main()

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_guard_checks_workflow_files(self, capsys: pytest.CaptureFixture) -> None:
        """standards_guard checks workflow files for supply chain risks."""
        from claude_cli.standards_guard import main

        payload = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": ".github/workflows/ci.yml",
                "content": "run: curl -sSL setup.sh | bash",
            },
        }

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = json.dumps(payload)
            main()

        captured = capsys.readouterr()
        assert "deny" in captured.out
        assert "curl|sudo/bash" in captured.out


class TestCheckModelVisionHook:
    """Integration tests for check_model_vision main()."""

    def test_vision_detected_via_ollama_show(self, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
        """check_model_vision detects vision from ollama show output."""
        monkeypatch.setenv("ANTHROPIC_DEFAULT_SONNET_MODEL", "llava:latest")
        monkeypatch.delenv("ANTHROPIC_DEFAULT_OPUS_MODEL", raising=False)
        monkeypatch.delenv("ANTHROPIC_DEFAULT_HAIKU_MODEL", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_SUBAGENT_MODEL", raising=False)

        from claude_cli.check_model_vision import main

        fake_stdout = "Capabilities\n  vision\n  tools\n"

        with patch(
            "claude_cli.check_model_vision.OllamaProvider.show_model",
            return_value=(fake_stdout, True),
        ):
            with patch(
                "claude_cli.check_model_vision.OllamaProvider.list_models",
                return_value=[],
            ):
                with patch(
                    "claude_cli.check_model_vision.get_active_model",
                    return_value=None,
                ):
                    main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["models"]["ANTHROPIC_DEFAULT_SONNET_MODEL"]["vision"] is True

    def test_vision_false_when_not_in_caps(self, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
        """check_model_vision returns false when vision not in capabilities."""
        monkeypatch.setenv("ANTHROPIC_DEFAULT_SONNET_MODEL", "granite:latest")

        from claude_cli.check_model_vision import main

        fake_stdout = "Capabilities\n  tools\n"

        with patch(
            "claude_cli.check_model_vision.OllamaProvider.show_model",
            return_value=(fake_stdout, True),
        ):
            with patch(
                "claude_cli.check_model_vision.OllamaProvider.list_models",
                return_value=[],
            ):
                with patch(
                    "claude_cli.check_model_vision.get_active_model",
                    return_value=None,
                ):
                    main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["models"]["ANTHROPIC_DEFAULT_SONNET_MODEL"]["vision"] is False

    def test_fallback_to_known_vision_remote(self, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
        """check_model_vision falls back to known vision-capable remotes."""
        monkeypatch.setenv("ANTHROPIC_DEFAULT_SONNET_MODEL", "deepseek-vl:latest")

        from claude_cli.check_model_vision import main

        with patch(
            "claude_cli.check_model_vision.OllamaProvider.show_model",
            return_value=("", False),
        ):
            with patch(
                "claude_cli.check_model_vision.OllamaProvider.list_models",
                return_value=[
                    {"name": "deepseek-vl:latest", "remote_model": "deepseek-vl"}
                ],
            ):
                with patch(
                    "claude_cli.check_model_vision.get_active_model",
                    return_value=None,
                ):
                    main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["models"]["ANTHROPIC_DEFAULT_SONNET_MODEL"]["vision"] is True

    def test_empty_env_outputs_nothing(self, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
        """check_model_vision outputs empty models when no env vars set."""
        for var in [
            "ANTHROPIC_DEFAULT_OPUS_MODEL",
            "ANTHROPIC_DEFAULT_SONNET_MODEL",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL",
            "CLAUDE_CODE_SUBAGENT_MODEL",
        ]:
            monkeypatch.delenv(var, raising=False)

        from claude_cli.check_model_vision import main

        with patch("claude_cli.check_model_vision.get_active_model", return_value=None):
            main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["models"] == {}
        assert output["any_vision_available"] is False
