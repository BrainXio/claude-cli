"""JSON schemas for work items and lifecycle events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class KanbanStatus(str, Enum):
    BACKLOG = "backlog"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    ARCHIVED = "archived"


class Priority(int, Enum):
    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4
    P5 = 5


@dataclass
class WorkItem:
    """A unit of work tracked through the KB system."""

    task_id: str
    subject: str
    description: str = ""
    kanban_status: KanbanStatus = KanbanStatus.BACKLOG
    priority: Priority = Priority.P3
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    due_by: datetime | None = None
    assigned_to: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "subject": self.subject,
            "description": self.description,
            "kanban_status": self.kanban_status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "due_by": self.due_by.isoformat() if self.due_by else None,
            "assigned_to": self.assigned_to,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkItem:
        return cls(
            task_id=data["task_id"],
            subject=data["subject"],
            description=data.get("description", ""),
            kanban_status=KanbanStatus(data.get("kanban_status", "backlog")),
            priority=Priority(data.get("priority", 3)),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            due_by=datetime.fromisoformat(data["due_by"])
            if data.get("due_by")
            else None,
            assigned_to=data.get("assigned_to"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class WorkLifecycleEvent:
    """An event recording a transition in a work item's lifecycle."""

    task_id: str
    from_status: KanbanStatus
    to_status: KanbanStatus
    timestamp: datetime = field(default_factory=datetime.now)
    actor: str = "system"
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "from_status": self.from_status.value,
            "to_status": self.to_status.value,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "reason": self.reason,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkLifecycleEvent:
        return cls(
            task_id=data["task_id"],
            from_status=KanbanStatus(data["from_status"]),
            to_status=KanbanStatus(data["to_status"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            actor=data.get("actor", "system"),
            reason=data.get("reason", ""),
            metadata=data.get("metadata", {}),
        )


def validate_work_item(data: dict[str, Any]) -> list[str]:
    """Validate a dict against the WorkItem schema. Returns list of errors."""
    errors: list[str] = []
    required = {"task_id", "subject"}
    missing = required - set(data.keys())
    if missing:
        errors.append(f"Missing required fields: {sorted(missing)}")
    if "kanban_status" in data and data["kanban_status"] not in {
        s.value for s in KanbanStatus
    }:
        errors.append(f"Invalid kanban_status: {data['kanban_status']}")
    return errors


def validate_lifecycle_event(data: dict[str, Any]) -> list[str]:
    """Validate a dict against the WorkLifecycleEvent schema. Returns list of errors."""
    errors: list[str] = []
    required = {"task_id", "from_status", "to_status"}
    missing = required - set(data.keys())
    if missing:
        errors.append(f"Missing required fields: {sorted(missing)}")
    for field_name in ("from_status", "to_status"):
        if field_name in data and data[field_name] not in {
            s.value for s in KanbanStatus
        }:
            errors.append(f"Invalid {field_name}: {data[field_name]}")
    return errors
