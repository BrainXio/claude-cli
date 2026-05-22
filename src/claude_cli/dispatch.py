#!/usr/bin/env python3
"""Workflow dispatch engine — reads workflow JSON, evaluates tier gates, outputs execution plan."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

WORKFLOW_DIR = Path(__file__).resolve().parent.parent.parent / "claude-workflows"
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
        return json.load(f)  # type: ignore[no-any-return]


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


def load_workflow(name: str) -> dict[str, Any]:
    path = WORKFLOW_DIR / f"{name}.json"
    if not path.exists():
        print(f"Workflow '{name}' not found at {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return json.load(f)  # type: ignore[no-any-return]


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

    def visit(name: str, stack: set[str]) -> None:
        if name in visited:
            return
        if name in stack:
            raise ValueError(f"Circular dependency detected involving '{name}'")
        stack.add(name)
        stage = by_name[name]
        for dep in stage.get("depends_on", []):
            visit(dep, stack)
        stack.discard(name)
        visited.add(name)
        order.append(stage)

    for stage in stages:
        visit(stage["name"], set())

    return order


def group_parallel(stages: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Group stages that can run in parallel into batches."""
    batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_deps: set[str] = set()

    for stage in stages:
        deps = set(stage.get("depends_on", []))
        if deps <= current_deps:
            current.append(stage)
        else:
            if current:
                batches.append(current)
            current = [stage]
        current_deps.add(stage["name"])

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
