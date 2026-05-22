"""Tests for claude_quality.schemas."""

from datetime import datetime

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


def test_validate_lifecycle_event_missing_fields() -> None:
    """Test validation errors for missing required fields."""
    errors = validate_lifecycle_event({})
    assert "task_id" in str(errors)


def test_validate_lifecycle_event_invalid_status() -> None:
    """Test validation errors for invalid status values."""
    errors = validate_lifecycle_event(
        {"task_id": "t", "from_status": "invalid", "to_status": "in_progress"}
    )
    assert "from_status" in str(errors)


def test_validate_lifecycle_event_both_invalid() -> None:
    """Test validation with both statuses invalid."""
    errors = validate_lifecycle_event(
        {"task_id": "t", "from_status": "nope", "to_status": "wrong"}
    )
    assert "from_status" in str(errors)
    assert "to_status" in str(errors)


def test_work_item_with_all_fields() -> None:
    """Test WorkItem with all optional fields set."""
    now = datetime.now()
    wi = WorkItem(
        task_id="test-1",
        subject="Test subject",
        description="A description",
        kanban_status=KanbanStatus.DONE,
        priority=Priority.P0,
        due_by=now,
        assigned_to="user@example.com",
        tags=["bug", "urgent"],
        metadata={"key": "value"},
    )
    data = wi.to_dict()
    restored = WorkItem.from_dict(data)
    assert restored.task_id == wi.task_id
    assert restored.subject == wi.subject
    assert restored.due_by == wi.due_by


def test_work_item_with_none_values() -> None:
    """Test WorkItem with None values for optional fields."""
    wi = WorkItem(
        task_id="test-1",
        subject="Test subject",
        assigned_to=None,
        due_by=None,
        tags=[],
        metadata={},
    )
    data = wi.to_dict()
    assert data["assigned_to"] is None
    assert data["due_by"] is None
    assert data["tags"] == []
    assert data["metadata"] == {}


def test_lifecycle_event_with_reason_and_metadata() -> None:
    """Test WorkLifecycleEvent with reason and metadata."""
    event = WorkLifecycleEvent(
        task_id="test-1",
        from_status=KanbanStatus.READY,
        to_status=KanbanStatus.IN_PROGRESS,
        actor="user@example.com",
        reason="Starting implementation",
        metadata={"priority_change": "high"},
    )
    data = event.to_dict()
    assert data["reason"] == "Starting implementation"
    assert data["metadata"] == {"priority_change": "high"}
    restored = WorkLifecycleEvent.from_dict(data)
    assert restored.actor == "user@example.com"
    assert restored.reason == "Starting implementation"


def test_work_item_custom_priority() -> None:
    """Test WorkItem with custom priority levels."""
    for priority in Priority:
        wi = WorkItem(task_id="test", subject="Test", priority=priority)
        assert wi.priority == priority


def test_work_item_kanban_status_all() -> None:
    """Test WorkItem with all kanban status values."""
    for status in KanbanStatus:
        wi = WorkItem(task_id="test", subject="Test", kanban_status=status)
        assert wi.kanban_status == status


def test_work_item_created_at_auto_set() -> None:
    """Test that created_at is automatically set."""
    wi = WorkItem(task_id="test", subject="Test")
    assert wi.created_at is not None


def test_work_item_updated_at_auto_set() -> None:
    """Test that updated_at is automatically set."""
    wi = WorkItem(task_id="test", subject="Test")
    assert wi.updated_at is not None


def test_validate_work_item_empty_dict() -> None:
    """Test validation of empty dict."""
    errors = validate_work_item({})
    # Should have errors for both required fields
    assert len(errors) == 1
    error = errors[0]
    assert "task_id" in error
    assert "subject" in error


def test_validate_work_item_valid_minimal() -> None:
    """Test validation of minimal valid work item."""
    errors = validate_work_item({"task_id": "t-1", "subject": "Test subject"})
    assert errors == []


def test_validate_lifecycle_event_valid_minimal() -> None:
    """Test validation of minimal valid lifecycle event."""
    errors = validate_lifecycle_event(
        {"task_id": "t", "from_status": "backlog", "to_status": "ready"}
    )
    assert errors == []


def test_validate_lifecycle_event_extra_fields_allowed() -> None:
    """Test that extra fields are allowed in validation."""
    errors = validate_lifecycle_event(
        {
            "task_id": "t",
            "from_status": "backlog",
            "to_status": "ready",
            "extra_field": "should be ignored",
        }
    )
    assert errors == []


def test_priority_enum_order() -> None:
    """Test that Priority enum has correct ordering (P0 highest)."""
    assert Priority.P0.value < Priority.P1.value
    assert Priority.P1.value < Priority.P2.value
    assert Priority.P2.value < Priority.P3.value
    assert Priority.P3.value < Priority.P4.value
    assert Priority.P4.value < Priority.P5.value


def test_kanban_status_enum_values() -> None:
    """Test that all KanbanStatus enum values are defined correctly."""
    assert KanbanStatus.BACKLOG.value == "backlog"
    assert KanbanStatus.READY.value == "ready"
    assert KanbanStatus.IN_PROGRESS.value == "in_progress"
    assert KanbanStatus.BLOCKED.value == "blocked"
    assert KanbanStatus.DONE.value == "done"
    assert KanbanStatus.ARCHIVED.value == "archived"
