#!/usr/bin/env python3
"""Workflow dispatch engine — reads workflow JSON, evaluates tier gates, outputs execution plan."""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, cast

from ._hook_metrics import timed_hook


def _resolve_workflow_dir() -> Path:
    env = os.environ.get("CLAUDE_WORKFLOWS_DIR", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    try:
        from importlib.resources import files

        pkg = files("claude_cli")
        if pkg:
            candidate = Path(str(pkg)).parent.parent / "claude-workflows"
            if candidate.exists():
                return candidate.resolve()
    except (ImportError, ModuleNotFoundError, TypeError):
        pass
    fallback = Path(__file__).resolve().parent.parent.parent / "claude-workflows"
    return fallback


WORKFLOW_DIR = _resolve_workflow_dir()
STATE_PATH = Path.home() / ".claude/data/state.json"

PROFILE_TIERS: dict[str, int] = {
    "worker-cloud": 1,
    "worker-local": 0,
    "helper-cloud": 3,
    "helper-hybrid": 3,
    "helper-local": 2,
    "trainer-cloud": 5,
    "trainer-hybrid": 4,
    "trainer-local": 4,
}

MODE_TIERS: dict[str, int] = {
    "worker": 1,
    "helper": 3,
    "trainer": 5,
}


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    with open(STATE_PATH) as f:
        return cast(dict[str, Any], json.load(f))


def get_tier(state: dict[str, Any]) -> int:
    profile = state.get("profile", "")
    if isinstance(profile, str) and profile in PROFILE_TIERS:
        return PROFILE_TIERS[profile]
    if isinstance(profile, dict):
        return int(profile.get("tier", 0))
    # Fall back to hardware.default_role when profile is absent
    hardware = state.get("hardware", {})
    role = hardware.get("default_role", "")
    if isinstance(role, str):
        return MODE_TIERS.get(role, 0)
    return 0


def _validate_workflow_structural(data: dict[str, Any]) -> None:
    """Lightweight structural validation without external dependencies.

    Checks required keys and basic types against _workflow_schema.json.
    Raises ValueError with a descriptive message on failure.
    """
    if not isinstance(data, dict):
        raise ValueError("Workflow root must be an object")
    if "workflow" not in data or not isinstance(data["workflow"], str) or not data["workflow"]:
        raise ValueError("Workflow must have a non-empty 'workflow' string")
    if "stages" not in data or not isinstance(data["stages"], list):
        raise ValueError("Workflow must have a 'stages' array")

    stage_names: set[str] = set()
    for idx, stage in enumerate(data["stages"]):
        if not isinstance(stage, dict):
            raise ValueError(f"Stage {idx} must be an object")
        name = stage.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"Stage {idx} must have a non-empty 'name' string")
        if name in stage_names:
            raise ValueError(f"Duplicate stage name: '{name}'")
        stage_names.add(name)

        for key, expected in (
            ("parallel", bool),
            ("max_concurrent", int),
        ):
            if key in stage and not isinstance(stage[key], expected):
                raise ValueError(
                    f"Stage '{name}': '{key}' must be {expected.__name__}, got {type(stage[key]).__name__}"
                )
        if "depends_on" in stage:
            deps = stage["depends_on"]
            if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
                raise ValueError(f"Stage '{name}': 'depends_on' must be a list of strings")
        if "isolation" in stage:
            val = stage["isolation"]
            if val not in ("none", "worktree", "container"):
                raise ValueError(f"Stage '{name}': 'isolation' must be one of none|worktree|container")


def load_workflow(name: str) -> dict[str, Any]:
    path = WORKFLOW_DIR / f"{name}.json"
    if not path.exists():
        available = sorted(p.stem for p in WORKFLOW_DIR.glob("*.json")) if WORKFLOW_DIR.exists() else []
        hint = ""
        if available:
            hint = f" Available workflows: {', '.join(available)}."
        print(
            f"Workflow '{name}' not found at {path}."
            f"{hint}"
            f" Set CLAUDE_WORKFLOWS_DIR to override the search path.",
            file=sys.stderr,
        )
        sys.exit(1)
    with open(path) as f:
        data: dict[str, Any] = json.load(f)
    try:
        _validate_workflow_structural(data)
    except ValueError as exc:
        print(
            f"Workflow '{name}' validation failed: {exc}"
            f" (see src/claude_cli/_workflow_schema.json for the expected schema)",
            file=sys.stderr,
        )
        sys.exit(1)
    return data


def evaluate_gate(gate: str, tier: int) -> bool:
    gate = gate.strip()
    if gate == "always":
        return True
    if gate.startswith("tier >= "):
        try:
            required = int(gate.replace("tier >= ", "").strip())
            return tier >= required
        except ValueError:
            return False
    return False


def topological_sort(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return stages in dependency order, grouped for parallel execution."""
    by_name = {s["name"]: s for s in stages}
    visited: set[str] = set()
    order: list[dict[str, Any]] = []

    def visit(name: str, stack: list[str]) -> None:
        if name in visited:
            return
        if name in stack:
            cycle = " -> ".join(stack[stack.index(name):] + [name])
            raise ValueError(f"Circular dependency detected: {cycle}")
        stack.append(name)
        stage = by_name[name]
        for dep in stage.get("depends_on", []):
            if dep not in by_name:
                raise ValueError(
                    f"Stage '{name}' depends on unknown stage '{dep}'."
                    f" Available stages: {', '.join(sorted(by_name))}"
                )
            visit(dep, stack)
        stack.pop()
        visited.add(name)
        order.append(stage)

    for stage in stages:
        visit(stage["name"], [])

    return order


def group_parallel(stages: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Group stages that can run in parallel into batches."""
    batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    completed_deps: set[str] = set()

    for stage in stages:
        deps = set(stage.get("depends_on", []))
        if deps <= completed_deps:
            current.append(stage)
        else:
            if current:
                batches.append(current)
                for s in current:
                    completed_deps.add(s["name"])
            current = [stage]

    if current:
        batches.append(current)

    return batches


def build_plan(
    workflow: dict[str, Any], tier: int, stage_filter: str | None = None
) -> dict[str, Any]:
    stages = workflow.get("stages", [])
    plan_stages = []

    for stage in stages:
        if stage_filter and stage["name"] != stage_filter:
            continue

        gate = stage.get("gate", "always")
        passed = evaluate_gate(gate, tier)
        fallback = stage.get("fallback", "skip")

        plan_stages.append(
            {
                "name": stage["name"],
                "agent": stage.get("agent", "general-purpose"),
                "gate": gate,
                "tier": tier,
                "gate_passed": passed,
                "fallback": fallback if not passed else None,
                "parallel": stage.get("parallel", False),
                "max_concurrent": stage.get("max_concurrent", 1),
                "isolation": stage.get("isolation", "none"),
                "depends_on": stage.get("depends_on", []),
                "output": stage.get("output", ""),
                "sub_agents": stage.get("sub_agents", []),
            }
        )

    return {
        "workflow": workflow.get("workflow", ""),
        "description": workflow.get("description", ""),
        "tier": tier,
        "stage_filter": stage_filter,
        "stages": plan_stages,
    }


def print_plan(plan: dict[str, Any], dry_run: bool = False) -> None:
    wf = plan["workflow"]
    tier = plan["tier"]
    stages = plan["stages"]
    stage_filter = plan["stage_filter"]

    mode = "DRY RUN" if dry_run else "EXECUTION PLAN"
    if stage_filter:
        mode += f" (stage: {stage_filter})"

    print(f"Workflow: {wf} ({len(stages)} stages)")
    print(f"Tier: {tier}")
    print(f"Mode: {mode}")
    print()
    print(f"{'Stage':<15} {'Gate':<15} {'Agent':<18} {'Parallel':<10} {'Status'}")
    print("-" * 75)

    for s in stages:
        status = "✅ will execute" if s["gate_passed"] else f"⏭️  {s['fallback']}"
        parallel = f"yes ({s['max_concurrent']})" if s["parallel"] else "no"
        print(
            f"{s['name']:<15} {s['gate']:<15} {s['agent']:<18} {parallel:<10} {status}"
        )


def main() -> None:
    with timed_hook("dispatch"):
        _run_dispatch()


def _run_dispatch() -> None:
    parser = argparse.ArgumentParser(description="Workflow dispatch engine")
    parser.add_argument("workflow", help="Workflow name (e.g., feature-implement)")
    parser.add_argument("--stage", help="Execute a single stage only")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show plan without executing"
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON plan")
    args = parser.parse_args()

    state = load_state()
    tier = get_tier(state)
    workflow = load_workflow(args.workflow)
    plan = build_plan(workflow, tier, args.stage)

    if args.json:
        print(json.dumps(plan, indent=2))
        return

    print_plan(plan, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
