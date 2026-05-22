"""Tests for claude_quality.modes (anti-gaming validator)."""

from claude_quality.anti_gaming import Principle, validate_proposal


def test_empty_proposal_fails() -> None:
    violations = validate_proposal("", concrete_failure=None)
    assert len(violations) > 0


def test_concrete_failure_prevents_speculative_warning() -> None:
    violations = validate_proposal(
        "Add a logging system",
        concrete_failure="Current system loses debug info on crashes",
    )
    # Should not trigger speculative warning if concrete failure is present
    speculative = [
        v for v in violations if v.principle == Principle.SOLVE_CURRENT_FAILURES
    ]
    assert len(speculative) == 0


def test_speculative_language_detected() -> None:
    violations = validate_proposal(
        "Add a logging system for when we need telemetry in the future",
        concrete_failure="none",
    )
    speculative = [
        v for v in violations if v.principle == Principle.SOLVE_CURRENT_FAILURES
    ]
    assert len(speculative) > 0


def test_activity_metric_detected() -> None:
    violations = validate_proposal(
        "Reward agents for bus activity and meeting attendance",
        concrete_failure="agents are not participating in meetings",
    )
    activity = [v for v in violations if v.principle == Principle.MEASURE_OUTCOMES]
    assert len(activity) > 0
