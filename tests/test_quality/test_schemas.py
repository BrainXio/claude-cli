"""Tests for claude_quality.schemas."""

from claude_quality.schemas import (
    KanbanStatus,
    Priority,
    WorkItem,
    WorkLifecycleEvent,
    validate_lifecycle_event,
    validate_work_item,
)


def test_work_item_defaults() -> None:
    wi = WorkItem(task_id="test-1", subject="Test subject")
    assert wi.kanban_status == KanbanStatus.BACKLOG
    assert wi.priority == Priority.P3
    assert wi.description == ""


def test_work_item_roundtrip() -> None:
    wi = WorkItem(
        task_id="test-1",
        subject="Test subject",
        description="A description",
        kanban_status=KanbanStatus.IN_PROGRESS,
        priority=Priority.P1,
        tags=["bug", "urgent"],
    )
    data = wi.to_dict()
    restored = WorkItem.from_dict(data)
    assert restored.task_id == wi.task_id
    assert restored.subject == wi.subject
    assert restored.kanban_status == wi.kanban_status
    assert restored.priority == wi.priority
    assert restored.tags == wi.tags


def test_lifecycle_event_roundtrip() -> None:
    event = WorkLifecycleEvent(
        task_id="test-1",
        from_status=KanbanStatus.BACKLOG,
        to_status=KanbanStatus.IN_PROGRESS,
        actor="user",
        reason="starting work",
    )
    data = event.to_dict()
    restored = WorkLifecycleEvent.from_dict(data)
    assert restored.task_id == event.task_id
    assert restored.from_status == event.from_status
    assert restored.to_status == event.to_status


def test_validate_work_item_missing_fields() -> None:
    errors = validate_work_item({})
    assert "task_id" in str(errors)


def test_validate_work_item_invalid_status() -> None:
    errors = validate_work_item(
        {"task_id": "t", "subject": "s", "kanban_status": "invalid"}
    )
    assert "kanban_status" in str(errors)


def test_validate_lifecycle_event_ok() -> None:
    errors = validate_lifecycle_event(
        {"task_id": "t", "from_status": "backlog", "to_status": "in_progress"}
    )
    assert errors == []
