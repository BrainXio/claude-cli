"""OUT OF SCOPE — Identity layer boundary module.

This module is explicitly EXCLUDED from the Claude CLI baseline
stabilization per PLAN.md Scope Boundary. The `_identity.py`
session/agent tracking layer belongs in a separate operational
layer and must not bleed into core CLI stabilization.

This adapter exists ONLY to prevent direct `_identity` imports
from spreading into `bootstrap.py` and other core hooks.
It is a containment boundary, not a feature. Do not expand it.
"""

from __future__ import annotations

import os
from typing import Any


def _import_identity() -> Any:
    """Lazy import of _identity to avoid module-level coupling."""
    from . import _identity

    return _identity


def register_and_resume(
    agent_name: str, task: str | None, branch: str, worktree: str | None
) -> tuple[dict[str, Any], list[str], int]:
    """Register bootstrap session and resume any previous sessions.

    Returns (session_record, resumed_items, migrated_tasks).
    """
    _identity = _import_identity()

    session_record = _identity.register_bootstrap_session(
        role="helper",
        agent_name=agent_name,
        task=task,
        branch=branch,
        worktree_path=worktree or None,
    )

    resumed_items: list[str] = []
    migrated_tasks = 0

    agent_sessions = [
        s
        for s in _identity.list_active_sessions()
        if s["agent_id"] == session_record["agent_id"]
        and s["session_id"] != session_record["session_id"]
    ]

    for prev in sorted(agent_sessions, key=lambda s: s.get("started_at", "")):
        summary = _identity.get_queue_summary(prev["session_id"])
        if summary.get("total", 0) > 0:
            resumed_items.append(
                f"  Previous session {prev['session_id']}: "
                f"{summary['total']} queued tasks"
            )
            for task_item in prev.get("work_queue", []):
                if task_item.get("status") == "queued":
                    _identity.push_task_to_queue(
                        session_record["session_id"],
                        task_item["id"],
                        task_item["subject"],
                        task_item.get("description", ""),
                        task_item.get("priority", 3),
                        task_item.get("due_by"),
                    )
                    migrated_tasks += 1
        for wi in prev.get("work_items", []):
            if wi not in session_record["work_items"]:
                session_record["work_items"].append(wi)
        _identity.update_session_activity(prev["session_id"], status="ended")

    return session_record, resumed_items, migrated_tasks


def handle_batch(
    batch_id: str, session_record: dict[str, Any]
) -> dict[str, Any]:
    """Mark batch executed and mutate session_record with batch metadata.

    Returns updated session_record.
    """
    _identity = _import_identity()
    _identity.mark_batch_executed(batch_id, session_record["session_id"])
    print(f"\n[Batch Mode] Executing batch session {batch_id}")
    task_prompt = os.environ.get("CLAUDE_BATCH_TASK", "")
    print(f"  Task: {task_prompt[:80]}...")
    session_record["is_batch"] = True
    session_record["batch_id"] = batch_id
    _identity.save_session_record(session_record)
    return session_record
