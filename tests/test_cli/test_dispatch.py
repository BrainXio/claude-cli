"""Tests for claude_cli.dispatch."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, "/home/mister-robot/workspace/claude-cli/src")


def test_get_tier_with_profile():
    """Test get_tier with valid profile string."""
    from claude_cli.dispatch import get_tier

    state = {"profile": "worker-cloud"}
    tier = get_tier(state)
    assert tier == 1


def test_get_tier_with_profile_dict():
    """Test get_tier with profile as dict."""
    from claude_cli.dispatch import get_tier

    state = {"profile": {"tier": 3}}
    tier = get_tier(state)
    assert tier == 3


def test_get_tier_with_hardware_role():
    """Test get_tier falls back to hardware.default_role when profile absent."""
    from claude_cli.dispatch import get_tier

    state = {"hardware": {"default_role": "helper"}}
    tier = get_tier(state)
    assert tier == 3


def test_get_tier_empty_state():
    """Test get_tier with empty state returns 0."""
    from claude_cli.dispatch import get_tier

    state = {}
    tier = get_tier(state)
    assert tier == 0


def test_load_workflow_exists():
    """Test load_workflow finds and loads an existing workflow."""
    from claude_cli.dispatch import load_workflow, WORKFLOW_DIR

    # Create a test workflow
    test_workflow_dir = WORKFLOW_DIR
    test_workflow_file = test_workflow_dir / "test-workflow.json"
    test_workflow_file.write_text(json.dumps({
        "workflow": "test-workflow",
        "description": "Test workflow",
        "stages": []
    }))

    try:
        workflow = load_workflow("test-workflow")
        assert workflow["workflow"] == "test-workflow"
    finally:
        test_workflow_file.unlink()


def test_load_workflow_not_found():
    """Test load_workflow exits with error when workflow not found."""
    import pytest
    from claude_cli import dispatch
    from pathlib import Path

    orig_workflow_dir = dispatch.WORKFLOW_DIR
    dispatch.WORKFLOW_DIR = Path("/nonexistent/workflows")

    try:
        with pytest.raises(SystemExit) as exc_info:
            dispatch.load_workflow("nonexistent-workflow")
        assert exc_info.value.code == 1
    finally:
        dispatch.WORKFLOW_DIR = orig_workflow_dir


def test_evaluate_gate_always():
    """Test evaluate_gate with 'always' gate."""
    from claude_cli.dispatch import evaluate_gate

    result = evaluate_gate("always", 0)
    assert result is True


def test_evaluate_gate_tier():
    """Test evaluate_gate with tier >= gate."""
    from claude_cli.dispatch import evaluate_gate

    assert evaluate_gate("tier >= 3", 5) is True
    assert evaluate_gate("tier >= 3", 3) is True
    assert evaluate_gate("tier >= 5", 3) is False
    assert evaluate_gate("tier >= 0", 0) is True


def test_evaluate_gate_invalid():
    """Test evaluate_gate with invalid gate format."""
    from claude_cli.dispatch import evaluate_gate

    result = evaluate_gate("tier >= abc", 5)
    assert result is False


def test_topological_sort_no_deps():
    """Test topological_sort with no dependencies."""
    from claude_cli.dispatch import topological_sort

    stages = [
        {"name": "a"},
        {"name": "b"},
        {"name": "c"},
    ]

    result = topological_sort(stages)
    assert [s["name"] for s in result] == ["a", "b", "c"]


def test_topological_sort_with_deps():
    """Test topological_sort with dependencies."""
    from claude_cli.dispatch import topological_sort

    stages = [
        {"name": "a"},
        {"name": "b", "depends_on": ["a"]},
        {"name": "c", "depends_on": ["b"]},
    ]

    result = topological_sort(stages)
    names = [s["name"] for s in result]
    assert names.index("a") < names.index("b")
    assert names.index("b") < names.index("c")


def test_topological_sort_circular():
    """Test topological_sort raises on circular dependency."""
    from claude_cli.dispatch import topological_sort
    import pytest

    stages = [
        {"name": "a", "depends_on": ["c"]},
        {"name": "b", "depends_on": ["a"]},
        {"name": "c", "depends_on": ["b"]},
    ]

    with pytest.raises(ValueError):
        topological_sort(stages)


def test_group_parallel_single_batch():
    """Test group_parallel returns single batch when all can run together."""
    from claude_cli.dispatch import group_parallel

    stages = [
        {"name": "a", "depends_on": []},
        {"name": "b", "depends_on": []},
        {"name": "c", "depends_on": []},
    ]

    result = group_parallel(stages)
    assert len(result) == 1
    assert [s["name"] for s in result[0]] == ["a", "b", "c"]


def test_group_parallel_multiple_batches():
    """Test group_parallel creates multiple batches for dependent stages."""
    from claude_cli.dispatch import group_parallel

    stages = [
        {"name": "a", "depends_on": []},
        {"name": "b", "depends_on": ["a"]},
        {"name": "c", "depends_on": ["a", "b"]},
    ]

    result = group_parallel(stages)
    assert len(result) == 3
    assert result[0][0]["name"] == "a"
    assert result[1][0]["name"] == "b"
    assert result[2][0]["name"] == "c"


def test_build_plan_all_passed():
    """Test build_plan with all gates passing."""
    from claude_cli.dispatch import build_plan

    workflow = {
        "workflow": "test",
        "description": "Test workflow",
        "stages": [
            {"name": "stage1", "gate": "tier >= 0"},
            {"name": "stage2", "gate": "tier >= 5"},
        ],
    }

    plan = build_plan(workflow, tier=10)
    assert plan["workflow"] == "test"
    assert len(plan["stages"]) == 2
    assert plan["stages"][0]["gate_passed"] is True
    assert plan["stages"][1]["gate_passed"] is True


def test_build_plan_stage_filter():
    """Test build_plan with stage_filter."""
    from claude_cli.dispatch import build_plan

    workflow = {
        "workflow": "test",
        "description": "Test workflow",
        "stages": [
            {"name": "stage1", "gate": "always"},
            {"name": "stage2", "gate": "always"},
        ],
    }

    plan = build_plan(workflow, tier=10, stage_filter="stage2")
    assert len(plan["stages"]) == 1
    assert plan["stages"][0]["name"] == "stage2"


def test_print_plan(capsys):
    """Test print_plan output format."""
    from claude_cli.dispatch import print_plan

    plan = {
        "workflow": "test",
        "tier": 3,
        "stages": [
            {"name": "a", "gate": "always", "agent": "test-agent",
             "gate_passed": True, "fallback": None, "parallel": False,
             "max_concurrent": 1, "depends_on": [], "output": "",
             "sub_agents": []},
        ],
        "stage_filter": None,
    }

    print_plan(plan, dry_run=True)
    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out
    assert "test" in captured.out


def test_print_plan_with_stage_filter(capsys):
    """Test print_plan with stage filter."""
    from claude_cli.dispatch import print_plan

    plan = {
        "workflow": "test",
        "tier": 3,
        "stages": [
            {"name": "a", "gate": "always", "agent": "test-agent",
             "gate_passed": True, "fallback": None, "parallel": False,
             "max_concurrent": 1, "depends_on": [], "output": "",
             "sub_agents": []},
        ],
        "stage_filter": "a",
    }

    print_plan(plan, dry_run=False)
    captured = capsys.readouterr()
    assert "(stage: a)" in captured.out


def test_main_with_json_output(capsys):
    """Test main() with --json flag."""
    from claude_cli.dispatch import main

    # Create a test workflow
    test_workflow_dir = Path("/home/mister-robot/workspace/claude-cli/claude-workflows")
    test_workflow_dir.mkdir(exist_ok=True)
    test_workflow_file = test_workflow_dir / "test.json"
    test_workflow_file.write_text(json.dumps({
        "workflow": "test",
        "description": "Test",
        "stages": []
    }))

    try:
        with patch("sys.argv", ["dispatch", "test", "--json"]):
            main()
            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["workflow"] == "test"
    finally:
        test_workflow_file.unlink()


def test_main_with_dry_run(capsys):
    """Test main() with --dry-run flag."""
    from claude_cli.dispatch import main

    test_workflow_dir = Path("/home/mister-robot/workspace/claude-cli/claude-workflows")
    test_workflow_dir.mkdir(exist_ok=True)
    test_workflow_file = test_workflow_dir / "test.json"
    test_workflow_file.write_text(json.dumps({
        "workflow": "test",
        "description": "Test",
        "stages": []
    }))

    try:
        with patch("sys.argv", ["dispatch", "test", "--dry-run"]):
            main()
            captured = capsys.readouterr()
            assert "DRY RUN" in captured.out
    finally:
        test_workflow_file.unlink()


def test_main_with_stage_filter(capsys):
    """Test main() with --stage flag."""
    from claude_cli.dispatch import main

    test_workflow_dir = Path("/home/mister-robot/workspace/claude-cli/claude-workflows")
    test_workflow_dir.mkdir(exist_ok=True)
    test_workflow_file = test_workflow_dir / "test.json"
    test_workflow_file.write_text(json.dumps({
        "workflow": "test",
        "description": "Test",
        "stages": [
            {"name": "build", "gate": "always"},
            {"name": "test", "gate": "always"},
        ],
    }))

    try:
        with patch("sys.argv", ["dispatch", "test", "--stage", "test", "--json"]):
            main()
            captured = capsys.readouterr()
            output = json.loads(captured.out)
            assert len(output["stages"]) == 1
            assert output["stages"][0]["name"] == "test"
    finally:
        test_workflow_file.unlink()
