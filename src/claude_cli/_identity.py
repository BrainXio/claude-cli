"""Structured identity management for claude agents and sessions.

Replaces opaque agent-{uuid} identifiers with purpose-driven names:
  Agent:   {role}.{name}           → h.economy
  Session: {role}.{purpose}.{date}.{nonce} → h.impl-economy-mcp.20260515.x7k2
"""

from __future__ import annotations

import json
import secrets
import string
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._config import DATA_DIR

AGENT_IDENTITY_FILE = DATA_DIR / "agent-identity.json"
SESSIONS_DIR = DATA_DIR / "sessions"

VALID_ROLES = {"w": "worker", "h": "helper", "t": "trainer", "m": "manual"}
VALID_PURPOSE_PREFIXES = {
    "meeting",
    "impl",
    "audit",
    "fix",
    "docs",
    "research",
    "ops",
    "plan",
}


def _generate_nonce(length: int = 4) -> str:
    """Generate a URL-safe nonce."""
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _today_compact() -> str:
    """Return today's date as yyyymmdd."""
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _sanitize_kebab(name: str) -> str:
    """Convert a string to kebab-case, ≤32 chars."""
    cleaned = name.lower()
    # Replace non-alphanumeric characters with hyphens
    cleaned = "".join(c if c.isalnum() or c == "-" else "-" for c in cleaned)
    # Collapse multiple hyphens into one
    import re

    cleaned = re.sub(r"-+", "-", cleaned)
    cleaned = cleaned.strip("-")
    return cleaned[:32]


def _validate_purpose(purpose: str) -> str:
    """Validate purpose starts with a known prefix."""
    purpose = _sanitize_kebab(purpose)
    parts = purpose.split("-", 1)
    prefix = parts[0]
    if prefix not in VALID_PURPOSE_PREFIXES:
        raise ValueError(
            f"Invalid purpose prefix '{prefix}'. Must be one of: {VALID_PURPOSE_PREFIXES}"
        )
    return purpose


def load_agent_identity(agent_id: str | None = None) -> dict[str, Any]:
    """Load agent identity from disk. Creates a default if missing."""
    if AGENT_IDENTITY_FILE.exists():
        try:
            data: dict[str, Any] = json.loads(
                AGENT_IDENTITY_FILE.read_text(encoding="utf-8")
            )
            if agent_id and data.get("agent_id") != agent_id:
                return _create_default_identity(agent_id)
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return _create_default_identity(agent_id)


def _create_default_identity(agent_id: str | None) -> dict[str, Any]:
    """Build a default identity record."""
    role, name = "w", "general"
    if agent_id and "." in agent_id:
        parts = agent_id.split(".", 1)
        role = parts[0] if parts[0] in VALID_ROLES else "w"
        name = parts[1] if parts[1] else "general"
    return {
        "agent_id": agent_id or f"{role}.{name}",
        "role": VALID_ROLES.get(role, "worker"),
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "public_key": None,
        "total_sessions": 0,
        "rolling_roi": 0.0,
        "error_rate": 0.0,
    }


def save_agent_identity(identity: dict[str, Any]) -> None:
    """Persist agent identity to disk."""
    AGENT_IDENTITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    AGENT_IDENTITY_FILE.write_text(
        json.dumps(identity, indent=2) + "\n", encoding="utf-8"
    )


def build_agent_id(role: str, name: str) -> str:
    """Build a structured agent identifier."""
    role = role[0].lower() if role else "w"
    if role not in VALID_ROLES:
        role = "w"
    name = _sanitize_kebab(name)
    if not name:
        name = "general"
    return f"{role}.{name}"


def build_session_id(
    role: str, purpose: str, date: str | None = None, nonce: str | None = None
) -> str:
    """Build a structured session identifier."""
    role = role[0].lower() if role else "w"
    if role not in VALID_ROLES:
        role = "w"
    purpose = _validate_purpose(purpose)
    date = date or _today_compact()
    nonce = nonce or _generate_nonce()
    return f"{role}.{purpose}.{date}.{nonce}"


def create_session_record(
    session_id: str,
    agent_id: str,
    role: str,
    purpose: str,
    branch: str = "main",
    worktree_path: str | None = None,
    work_items: list[str] | None = None,
    budget_id: str | None = None,
) -> dict[str, Any]:
    """Create a new session registry entry."""
    now = datetime.now(timezone.utc).isoformat()
    record: dict[str, Any] = {
        "session_id": session_id,
        "agent_id": agent_id,
        "role": VALID_ROLES.get(role[0].lower(), "worker"),
        "purpose": _validate_purpose(purpose),
        "status": "active",
        "started_at": now,
        "last_activity": now,
        "ended_at": None,
        "work_items": work_items or [],
        "work_queue": [],
        "meetings": [],
        "branch": branch,
        "worktree": worktree_path,
        "budget_id": budget_id,
        "heartbeat_count": 0,
        "idle_since": None,
        "escalation_level": 0,
    }
    return record


def save_session_record(record: dict[str, Any]) -> Path:
    """Persist a session record to ~/.claude/data/sessions/{session_id}.json."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = SESSIONS_DIR / f"{record['session_id']}.json"
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path


def load_session_record(session_id: str) -> dict[str, Any] | None:
    """Load a session record from disk."""
    path = SESSIONS_DIR / f"{session_id}.json"
    if not path.exists():
        return None
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data
    except (json.JSONDecodeError, OSError):
        return None


def update_session_activity(session_id: str, **fields: Any) -> bool:
    """Update fields on an existing session record."""
    record = load_session_record(session_id)
    if record is None:
        return False
    record["last_activity"] = datetime.now(timezone.utc).isoformat()
    record.update(fields)
    save_session_record(record)
    return True


def push_task_to_queue(
    session_id: str,
    task_id: str,
    subject: str,
    description: str = "",
    priority: int = 3,
    due_by: str | None = None,
) -> bool:
    """Push a bite-sized task onto an agent's work queue."""
    record = load_session_record(session_id)
    if record is None:
        return False
    queue: list[dict[str, Any]] = record.get("work_queue", [])
    task = {
        "id": task_id,
        "subject": subject,
        "description": description,
        "priority": priority,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "due_by": due_by,
        "status": "queued",
    }
    queue.append(task)
    record["work_queue"] = queue
    save_session_record(record)
    return True


def pop_task_from_queue(session_id: str) -> dict[str, Any] | None:
    """Pop the highest-priority task from the agent's work queue."""
    record = load_session_record(session_id)
    if record is None:
        return None
    queue: list[dict[str, Any]] = record.get("work_queue", [])
    if not queue:
        return None
    queue.sort(key=lambda t: (t.get("priority", 3), t.get("queued_at", "")))
    task = queue.pop(0)
    task["status"] = "claimed"
    task["claimed_at"] = datetime.now(timezone.utc).isoformat()
    record["work_queue"] = queue
    save_session_record(record)
    return task


def peek_next_task(session_id: str) -> dict[str, Any] | None:
    """Return the next task without removing it from the queue."""
    record = load_session_record(session_id)
    if record is None:
        return None
    queue: list[dict[str, Any]] = record.get("work_queue", [])
    if not queue:
        return None
    queue.sort(key=lambda t: (t.get("priority", 3), t.get("queued_at", "")))
    return queue[0]


def get_queue_summary(session_id: str) -> dict[str, Any]:
    """Return summary of an agent's work queue."""
    record = load_session_record(session_id)
    if record is None:
        return {"error": "session not found"}
    queue: list[dict[str, Any]] = record.get("work_queue", [])
    by_status: dict[str, int] = {}
    for t in queue:
        by_status[t.get("status", "queued")] = (
            by_status.get(t.get("status", "queued"), 0) + 1
        )
    return {
        "total": len(queue),
        "by_status": by_status,
        "next_task": peek_next_task(session_id),
    }


def list_active_sessions() -> list[dict[str, Any]]:
    """Return all session records with status != ended."""
    if not SESSIONS_DIR.exists():
        return []
    active: list[dict[str, Any]] = []
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            record: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            if record.get("status") != "ended":
                active.append(record)
        except (json.JSONDecodeError, OSError):
            continue
    return active


def infer_purpose_from_task(task: str | None) -> str:
    """Infer a purpose prefix from a free-form task description."""
    if not task:
        return "ops-general"
    task_lower = task.lower()
    mapping = {
        "meeting": "meeting",
        "impl": "impl",
        "implement": "impl",
        "audit": "audit",
        "review": "audit",
        "fix": "fix",
        "bug": "fix",
        "docs": "docs",
        "doc": "docs",
        "research": "research",
        "explore": "research",
        "ops": "ops",
        "monitor": "ops",
        "plan": "plan",
        "design": "plan",
    }
    for keyword, prefix in mapping.items():
        if keyword in task_lower:
            detail = _sanitize_kebab(task.replace(" ", "-").replace("_", "-"))[:20]
            return f"{prefix}-{detail}"
    return "ops-general"


def generate_structured_ids(
    role: str,
    agent_name: str,
    task: str | None = None,
    purpose: str | None = None,
    branch: str = "main",
) -> tuple[str, str]:
    """Generate both agent_id and session_id from role/name/task.

    Returns (agent_id, session_id).
    """
    agent_id = build_agent_id(role, agent_name)
    if purpose is None:
        purpose = infer_purpose_from_task(task)
    session_id = build_session_id(role, purpose)
    return agent_id, session_id


BATCH_SESSIONS_FILE = DATA_DIR / "batch_sessions.jsonl"


def schedule_batch_session(
    agent_id: str,
    cron: str,
    task_prompt: str,
    subject: str = "",
    max_duration_minutes: int = 30,
    work_items: list[str] | None = None,
) -> dict[str, Any]:
    """Schedule a cron-triggered batch session for an agent.

    Writes to ~/.claude/data/batch_sessions.jsonl.
    """
    now = datetime.now(timezone.utc).isoformat()
    batch_id = f"batch-{agent_id.replace('.', '-')}-{now.replace(':', '').replace('-', '').replace('.', '')}"
    record: dict[str, Any] = {
        "batch_id": batch_id,
        "agent_id": agent_id,
        "cron": cron,
        "task_prompt": task_prompt,
        "subject": subject or task_prompt[:50],
        "max_duration_minutes": max_duration_minutes,
        "work_items": work_items or [],
        "status": "scheduled",
        "scheduled_at": now,
        "executed_at": None,
        "completed_at": None,
        "result_summary": None,
    }
    BATCH_SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with BATCH_SESSIONS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return record


def list_scheduled_batches(agent_id: str | None = None) -> list[dict[str, Any]]:
    """Return scheduled batch sessions that have not been executed yet."""
    if not BATCH_SESSIONS_FILE.exists():
        return []
    batches: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in BATCH_SESSIONS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record: dict[str, Any] = json.loads(line)
            bid = record.get("batch_id")
            if not bid or bid in seen:
                continue
            seen.add(bid)
            if record.get("status") != "scheduled":
                continue
            if agent_id and record.get("agent_id") != agent_id:
                continue
            batches.append(record)
        except json.JSONDecodeError:
            continue
    return batches


def mark_batch_executed(batch_id: str, session_id: str) -> bool:
    """Mark a batch session as currently executing."""
    if not BATCH_SESSIONS_FILE.exists():
        return False
    lines = BATCH_SESSIONS_FILE.read_text(encoding="utf-8").splitlines()
    updated = False
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            record: dict[str, Any] = json.loads(line)
            if record.get("batch_id") == batch_id:
                record["status"] = "executing"
                record["executed_at"] = datetime.now(timezone.utc).isoformat()
                record["session_id"] = session_id
                lines[i] = json.dumps(record)
                updated = True
                break
        except json.JSONDecodeError:
            continue
    if updated:
        BATCH_SESSIONS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return updated


def complete_batch_session(
    batch_id: str, result_summary: str, success: bool = True
) -> bool:
    """Mark a batch session as completed with results."""
    if not BATCH_SESSIONS_FILE.exists():
        return False
    lines = BATCH_SESSIONS_FILE.read_text(encoding="utf-8").splitlines()
    updated = False
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            record: dict[str, Any] = json.loads(line)
            if record.get("batch_id") == batch_id:
                record["status"] = "completed" if success else "failed"
                record["completed_at"] = datetime.now(timezone.utc).isoformat()
                record["result_summary"] = result_summary
                lines[i] = json.dumps(record)
                updated = True
                break
        except json.JSONDecodeError:
            continue
    if updated:
        BATCH_SESSIONS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return updated


# WI-019 Phase 4: Cross-agent coverage matrix
COVERAGE_MATRIX_FILE = DATA_DIR / "coverage_matrix.json"
COVERAGE_IDLE_THRESHOLD_SECONDS: int = 1200  # 20 min


def assign_coverage(
    work_item_id: str, primary: str, secondary: str | None = None
) -> dict[str, Any]:
    """Assign primary and secondary owners to a work item for coverage."""
    matrix: dict[str, Any] = {}
    if COVERAGE_MATRIX_FILE.exists():
        try:
            matrix = json.loads(COVERAGE_MATRIX_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    matrix[work_item_id] = {
        "primary": primary,
        "secondary": secondary,
        "assigned_at": datetime.now(timezone.utc).isoformat(),
        "last_handoff": None,
    }
    COVERAGE_MATRIX_FILE.parent.mkdir(parents=True, exist_ok=True)
    COVERAGE_MATRIX_FILE.write_text(
        json.dumps(matrix, indent=2) + "\n", encoding="utf-8"
    )
    record: dict[str, Any] = matrix[work_item_id]
    return record


def get_coverage(work_item_id: str) -> dict[str, Any] | None:
    """Get coverage assignment for a work item."""
    if not COVERAGE_MATRIX_FILE.exists():
        return None
    try:
        matrix: dict[str, Any] = json.loads(
            COVERAGE_MATRIX_FILE.read_text(encoding="utf-8")
        )
        return matrix.get(work_item_id)
    except (json.JSONDecodeError, OSError):
        return None


def check_coverage_gaps() -> list[dict[str, Any]]:
    """Check for work items where primary is idle > threshold and secondary exists."""
    if not COVERAGE_MATRIX_FILE.exists():
        return []
    try:
        matrix: dict[str, Any] = json.loads(
            COVERAGE_MATRIX_FILE.read_text(encoding="utf-8")
        )
    except (json.JSONDecodeError, OSError):
        return []

    gaps: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    for wi_id, cov in matrix.items():
        primary = cov.get("primary")
        secondary = cov.get("secondary")
        if not primary or not secondary:
            continue
        # Check primary session activity
        primary_sessions = [
            s for s in list_active_sessions() if s["agent_id"] == primary
        ]
        if not primary_sessions:
            gaps.append(
                {
                    "work_item_id": wi_id,
                    "primary": primary,
                    "secondary": secondary,
                    "reason": "primary_offline",
                    "recommendation": f"Secondary {secondary} should take over {wi_id}",
                }
            )
            continue
        latest = max(
            (datetime.fromisoformat(s["last_activity"]) for s in primary_sessions),
            default=now,
        )
        idle_seconds = (now - latest).total_seconds()
        if idle_seconds > COVERAGE_IDLE_THRESHOLD_SECONDS:
            gaps.append(
                {
                    "work_item_id": wi_id,
                    "primary": primary,
                    "secondary": secondary,
                    "reason": "primary_idle",
                    "idle_seconds": int(idle_seconds),
                    "recommendation": f"Secondary {secondary} should take over {wi_id} (primary idle {int(idle_seconds // 60)}min)",
                }
            )
    return gaps


def register_bootstrap_session(
    role: str,
    agent_name: str,
    task: str | None = None,
    branch: str = "main",
    worktree_path: str | None = None,
) -> dict[str, Any]:
    """Full bootstrap registration: create identity + session, persist both.

    Returns the session record.
    """
    agent_id, session_id = generate_structured_ids(
        role, agent_name, task, branch=branch
    )

    identity = load_agent_identity(agent_id)
    identity["agent_id"] = agent_id
    identity["total_sessions"] = identity.get("total_sessions", 0) + 1
    save_agent_identity(identity)

    purpose = infer_purpose_from_task(task)
    record = create_session_record(
        session_id=session_id,
        agent_id=agent_id,
        role=role,
        purpose=purpose,
        branch=branch,
        worktree_path=worktree_path,
    )
    save_session_record(record)
    return record
