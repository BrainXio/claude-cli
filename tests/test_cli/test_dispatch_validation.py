"""Tests for dispatch.py workflow structural validation."""

import json
from pathlib import Path

import pytest

from claude_cli.dispatch import _validate_workflow_structural


class TestValidateWorkflowStructural:
    """Tests for _validate_workflow_structural."""

    def test_valid_workflow_passes(self) -> None:
        """Minimal valid workflow passes validation."""
        data = {
            "workflow": "test",
            "stages": [{"name": "stage1"}],
        }
        _validate_workflow_structural(data)  # does not raise

    def test_missing_workflow_key(self) -> None:
        """Missing 'workflow' key raises ValueError."""
        with pytest.raises(ValueError, match="non-empty 'workflow' string"):
            _validate_workflow_structural({"stages": []})

    def test_empty_workflow_string(self) -> None:
        """Empty 'workflow' string raises ValueError."""
        with pytest.raises(ValueError, match="non-empty 'workflow' string"):
            _validate_workflow_structural({"workflow": "", "stages": []})

    def test_non_string_workflow(self) -> None:
        """Non-string 'workflow' raises ValueError."""
        with pytest.raises(ValueError, match="non-empty 'workflow' string"):
            _validate_workflow_structural({"workflow": 123, "stages": []})

    def test_missing_stages_key(self) -> None:
        """Missing 'stages' key raises ValueError."""
        with pytest.raises(ValueError, match="'stages' array"):
            _validate_workflow_structural({"workflow": "test"})

    def test_non_array_stages(self) -> None:
        """Non-array 'stages' raises ValueError."""
        with pytest.raises(ValueError, match="'stages' array"):
            _validate_workflow_structural({"workflow": "test", "stages": "bad"})

    def test_stage_not_object(self) -> None:
        """Stage that is not an object raises ValueError."""
        with pytest.raises(ValueError, match="Stage 0 must be an object"):
            _validate_workflow_structural({"workflow": "test", "stages": ["bad"]})

    def test_stage_missing_name(self) -> None:
        """Stage without 'name' raises ValueError."""
        with pytest.raises(ValueError, match="non-empty 'name' string"):
            _validate_workflow_structural({"workflow": "test", "stages": [{"agent": "x"}]})

    def test_stage_empty_name(self) -> None:
        """Stage with empty 'name' raises ValueError."""
        with pytest.raises(ValueError, match="non-empty 'name' string"):
            _validate_workflow_structural({"workflow": "test", "stages": [{"name": ""}]})

    def test_duplicate_stage_names(self) -> None:
        """Duplicate stage names raise ValueError."""
        with pytest.raises(ValueError, match="Duplicate stage name"):
            _validate_workflow_structural(
                {
                    "workflow": "test",
                    "stages": [{"name": "a"}, {"name": "a"}],
                }
            )

    def test_invalid_parallel_type(self) -> None:
        """Non-boolean 'parallel' raises ValueError."""
        with pytest.raises(ValueError, match="'parallel' must be bool"):
            _validate_workflow_structural(
                {
                    "workflow": "test",
                    "stages": [{"name": "a", "parallel": "yes"}],
                }
            )

    def test_invalid_max_concurrent_type(self) -> None:
        """Non-int 'max_concurrent' raises ValueError."""
        with pytest.raises(ValueError, match="'max_concurrent' must be int"):
            _validate_workflow_structural(
                {
                    "workflow": "test",
                    "stages": [{"name": "a", "max_concurrent": "2"}],
                }
            )

    def test_invalid_depends_on_type(self) -> None:
        """Non-list 'depends_on' raises ValueError."""
        with pytest.raises(ValueError, match="'depends_on' must be a list of strings"):
            _validate_workflow_structural(
                {
                    "workflow": "test",
                    "stages": [{"name": "a", "depends_on": "b"}],
                }
            )

    def test_invalid_isolation_value(self) -> None:
        """Invalid 'isolation' enum raises ValueError."""
        with pytest.raises(ValueError, match="none|worktree|container"):
            _validate_workflow_structural(
                {
                    "workflow": "test",
                    "stages": [{"name": "a", "isolation": "vm"}],
                }
            )

    def test_valid_isolation_values(self) -> None:
        """Valid isolation values pass."""
        for val in ("none", "worktree", "container"):
            data = {
                "workflow": "test",
                "stages": [{"name": "a", "isolation": val}],
            }
            _validate_workflow_structural(data)


class TestLoadWorkflowIntegration:
    """Integration tests for load_workflow validation."""

    def test_load_workflow_validates(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """load_workflow exits on invalid JSON structure."""
        monkeypatch.setattr("claude_cli.dispatch.WORKFLOW_DIR", tmp_path)
        wf = tmp_path / "bad.json"
        wf.write_text(json.dumps({"workflow": "", "stages": []}))

        from claude_cli.dispatch import load_workflow

        with pytest.raises(SystemExit) as ctx:
            load_workflow("bad")
        assert ctx.value.code == 1
