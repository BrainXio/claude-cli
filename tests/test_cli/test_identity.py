"""Tests for claude_cli._identity."""
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

sys.path.insert(0, "/home/mister-robot/workspace/claude-cli/src")


def test_generate_nonce():
    """Test _generate_nonce generates URL-safe nonce."""
    from claude_cli._identity import _generate_nonce
    nonce = _generate_nonce()
    assert len(nonce) == 4
    assert all(c in "abcdefghijklmnopqrstuvwxyz0123456789" for c in nonce)


def test_generate_nonce_different():
    """Test _generate_nonce generates unique values."""
    from claude_cli._identity import _generate_nonce
    nonces = {_generate_nonce() for _ in range(100)}
    assert len(nonces) == 100


def test_today_compact():
    """Test _today_compact returns yyyymmdd format."""
    from claude_cli._identity import _today_compact
    result = _today_compact()
    assert len(result) == 8
    assert result == datetime.now(timezone.utc).strftime("%Y%m%d")


def test_sanitize_kebab():
    """Test _sanitize_kebab converts to kebab-case."""
    from claude_cli._identity import _sanitize_kebab
    assert _sanitize_kebab("hello world") == "hello-world"
    assert _sanitize_kebab("Hello_World") == "hello-world"
    assert _sanitize_kebab("hello!!!world") == "hello-world"
    assert _sanitize_kebab("  hello  ") == "hello"


def test_build_agent_id():
    """Test build_agent_id creates proper agent ID."""
    from claude_cli._identity import build_agent_id
    assert build_agent_id("helper", "economy") == "h.economy"
    assert build_agent_id("worker", "test") == "w.test"
    assert build_agent_id("trainer", "monitor") == "t.monitor"


def test_build_agent_id_invalid_role():
    """Test build_agent_id falls back to worker for invalid role."""
    from claude_cli._identity import build_agent_id
    assert build_agent_id("invalid", "test") == "w.test"


def test_build_agent_id_empty_name():
    """Test build_agent_id uses 'general' for empty name."""
    from claude_cli._identity import build_agent_id
    assert build_agent_id("worker", "") == "w.general"


def test_build_session_id():
    """Test build_session_id creates proper session ID."""
    from claude_cli._identity import build_session_id
    result = build_session_id("helper", "meeting", "20240515", "x7k2")
    assert result == "h.meeting.20240515.x7k2"


def test_build_session_id_invalid_role():
    """Test build_session_id falls back to worker for invalid role."""
    from claude_cli._identity import build_session_id
    result = build_session_id("invalid", "impl", "20240515")
    assert result.startswith("w.impl.20240515.")


def test_build_session_id_no_date_nonce():
    """Test build_session_id generates date and nonce when not provided."""
    from claude_cli._identity import build_session_id
    result = build_session_id("worker", "audit")
    parts = result.split(".")
    assert len(parts) == 4
    assert parts[0] == "w"
    assert parts[1] == "audit"


def test_create_session_record():
    """Test create_session_record creates proper session record."""
    from claude_cli._identity import create_session_record
    record = create_session_record(
        session_id="h.impl.test.20240515.x7k2",
        agent_id="h.economy",
        role="helper",
        purpose="impl",
        branch="main",
        worktree_path="/workspace",
    )
    assert record["session_id"] == "h.impl.test.20240515.x7k2"
    assert record["agent_id"] == "h.economy"
    assert record["role"] == "helper"
    assert record["purpose"] == "impl"
    assert record["status"] == "active"
    assert record["branch"] == "main"
    assert record["worktree"] == "/workspace"


def test_create_session_record_defaults():
    """Test create_session_record with defaults."""
    from claude_cli._identity import create_session_record
    record = create_session_record(
        session_id="w.test.20240515.x7k2",
        agent_id="w.general",
        role="worker",
        purpose="impl",
    )
    assert record["branch"] == "main"
    assert record["worktree"] is None
    assert record["budget_id"] is None


def test_infer_purpose_from_task():
    """Test infer_purpose_from_task infers purpose from task."""
    from claude_cli._identity import infer_purpose_from_task
    assert "meeting" in infer_purpose_from_task("Team meeting tomorrow")
    assert "impl" in infer_purpose_from_task("Implement new feature")
    assert "audit" in infer_purpose_from_task("Review code changes")
    assert "fix" in infer_purpose_from_task("Fix bug in login")
    assert "docs" in infer_purpose_from_task("Update documentation")
    assert "ops" in infer_purpose_from_task("Monitor system health")
    assert "plan" in infer_purpose_from_task("Plan release")


def test_infer_purpose_from_task_none():
    """Test infer_purpose_from_task returns ops-general for None."""
    from claude_cli._identity import infer_purpose_from_task
    assert infer_purpose_from_task(None) == "ops-general"


def test_generate_structured_ids():
    """Test generate_structured_ids generates both agent and session IDs."""
    from claude_cli._identity import generate_structured_ids
    agent_id, session_id = generate_structured_ids(
        "helper", "economy", "Implement economy features"
    )
    assert agent_id == "h.economy"
    assert session_id.startswith("h.impl-")
