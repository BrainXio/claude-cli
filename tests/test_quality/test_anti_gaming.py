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


def test_credit_system_detected() -> None:
    """Test that credit system without currency anchor is detected."""
    violations = validate_proposal(
        "Use a credit system for tracking agent contributions",
        concrete_failure="No way to measure agent value",
    )
    credit = [v for v in violations if v.principle == Principle.GROUND_IN_REALITY]
    assert len(credit) > 0


def test_credit_system_with_currency_passes() -> None:
    """Test that credit system with currency anchor passes."""
    violations = validate_proposal(
        "Use EUR credit system for tracking agent contributions",
        concrete_failure="No way to measure agent value",
        transaction_amount=100.0,
        transaction_currency="EUR",
    )
    credit = [v for v in violations if v.principle == Principle.GROUND_IN_REALITY]
    assert len(credit) == 0


def test_activity_metric_not_detected_when_absent() -> None:
    """Test that no activity violation when no activity keywords."""
    violations = validate_proposal(
        "Add feature X to solve problem Y",
        concrete_failure="Problem Y exists",
    )
    activity = [v for v in violations if v.principle == Principle.MEASURE_OUTCOMES]
    assert len(activity) == 0


def test_academic_phrase_detected() -> None:
    """Test that academic citation phrases are detected."""
    violations = validate_proposal(
        "According to the literature, we need a reflection layer",
        concrete_failure="Current system can't self-correct",
    )
    academic = [v for v in violations if v.principle == Principle.NO_ACADEMIC_VALIDATION]
    assert len(academic) > 0


def test_capability_gap_detected() -> None:
    """Test that capability gap assumptions are detected."""
    violations = validate_proposal(
        "When agents can reflect, add self-improvement",
        concrete_failure="Current system can't improve itself",
    )
    capability = [v for v in violations if v.principle == Principle.DESIGN_FOR_CURRENT]
    assert len(capability) > 0


def test_penalty_keyword_detected() -> None:
    """Test that penalty-based mechanisms are detected."""
    violations = validate_proposal(
        "Implement strike system for bad behavior",
        concrete_failure="Bad behavior persists",
    )
    penalty = [v for v in violations if v.principle == Principle.TRUST_UPWARD]
    assert len(penalty) > 0


def test_complexity_tax_detected() -> None:
    """Test that deferring maintenance is detected."""
    violations = validate_proposal(
        "We'll figure out maintenance later when we scale",
        concrete_failure="Current system is too slow",
    )
    complexity = [v for v in violations if v.principle == Principle.COMPLEXITY_TAX]
    assert len(complexity) > 0


def test_complexity_tax_with_fix() -> None:
    """Test that maintenance phrase in fix doesn't trigger violation."""
    violations = validate_proposal(
        "Add feature X",
        concrete_failure="Current system loses data",
        transaction_amount=100.0,
        transaction_currency="USD",
    )
    # Should only have no concrete failure violation if concrete failure is too short
    complexity = [v for v in violations if v.principle == Principle.COMPLEXITY_TAX]
    assert len(complexity) == 0


def test_full_valid_proposal() -> None:
    """Test that a valid proposal passes all checks."""
    violations = validate_proposal(
        "Add logging to save debug info on crashes so we don't lose debugging data when the app crashes",
        concrete_failure="Debug info is lost when the app crashes, making it impossible to debug production issues",
        transaction_amount=500.0,
        transaction_currency="USD",
    )
    assert len(violations) == 0


def test_multiple_violations_detected() -> None:
    """Test that multiple violations are all detected."""
    violations = validate_proposal(
        "According to research, add credit system with when agents can reflect",
        concrete_failure="none",
    )
    # Should have multiple violation types
    principles = set(v.principle for v in violations)
    # At minimum: no concrete failure + academic phrase
    assert len(principles) >= 2


def test_validate_proposal_empty_string_description() -> None:
    """Test that empty string description is detected."""
    violations = validate_proposal("", concrete_failure="none")
    # Should have multiple violations for empty/short input
    assert len(violations) > 0


def test_validate_proposal_short_concrete_failure() -> None:
    """Test that short concrete failure is detected."""
    violations = validate_proposal(
        "Add feature",
        concrete_failure="short",
    )
    # Should detect short concrete failure
    short_failure = [
        v for v in violations if v.principle == Principle.SOLVE_CURRENT_FAILURES
    ]
    assert len(short_failure) > 0


def test_validate_proposal_only_activity_metric() -> None:
    """Test detection of various activity metrics."""
    for kw in ["posts", "attendance", "labels generated", "meeting count", "bus activity", "channel messages"]:
        violations = validate_proposal(
            f"Reward {kw}",
            concrete_failure="problem exists",
        )
        activity = [v for v in violations if v.principle == Principle.MEASURE_OUTCOMES]
        assert len(activity) > 0, f"Should detect activity metric: {kw}"


def test_validate_proposal_only_academic_phrases() -> None:
    """Test detection of various academic citation phrases."""
    phrases = [
        "literature says",
        "research shows",
        "paper demonstrates",
        "according to",
        "studies indicate",
    ]
    for phrase in phrases:
        violations = validate_proposal(
            f"{phrase} we need a solution",
            concrete_failure="problem exists",
        )
        academic = [v for v in violations if v.principle == Principle.NO_ACADEMIC_VALIDATION]
        assert len(academic) > 0, f"Should detect academic phrase: {phrase}"


def test_validate_proposal_only_capability_gaps() -> None:
    """Test detection of various capability gap assumptions."""
    gaps = [
        "when agents can reflect",
        "once llm-as-judge is deployed",
        "future capability",
        "when we have",
    ]
    for gap in gaps:
        violations = validate_proposal(
            f"Add feature {gap}",
            concrete_failure="problem exists",
        )
        capability = [v for v in violations if v.principle == Principle.DESIGN_FOR_CURRENT]
        assert len(capability) > 0, f"Should detect capability gap: {gap}"


def test_validate_proposal_only_penalty_keywords() -> None:
    """Test detection of various penalty keywords."""
    keywords = ["strike", "penalty", "punish", "negligence multiplier", "error cost", "reputation score", "adversarial audit"]
    for kw in keywords:
        violations = validate_proposal(
            f"Implement {kw} system",
            concrete_failure="problem exists",
        )
        penalty = [v for v in violations if v.principle == Principle.TRUST_UPWARD]
        assert len(penalty) > 0, f"Should detect penalty keyword: {kw}"


def test_validate_proposal_complexity_tax_variations() -> None:
    """Test detection of complexity tax phrases."""
    phrases = ["we'll figure out", "maintenance later"]
    for phrase in phrases:
        violations = validate_proposal(
            f"We need feature, {phrase}",
            concrete_failure="problem exists",
        )
        complexity = [v for v in violations if v.principle == Principle.COMPLEXITY_TAX]
        assert len(complexity) > 0, f"Should detect complexity tax phrase: {phrase}"


def test_validate_proposal_multiple_principles_single_violation() -> None:
    """Test that a single proposal can trigger multiple principles."""
    violations = validate_proposal(
        "According to literature, we'll figure out maintenance later when we have credit system",
        concrete_failure="none",
    )
    # Should detect: academic phrase, complexity tax, credit system, no concrete failure
    principles = set(v.principle for v in violations)
    assert len(principles) >= 4


def test_validate_proposal_threshold_behavior() -> None:
    """Test that concrete_failure threshold is exactly 10 chars."""
    # 9 chars - should trigger
    violations = validate_proposal(
        "Feature",
        concrete_failure="123456789",
    )
    short_failure = [
        v for v in violations if v.principle == Principle.SOLVE_CURRENT_FAILURES
    ]
    assert len(short_failure) > 0

    # 10 chars - should pass (exact threshold)
    violations = validate_proposal(
        "Feature",
        concrete_failure="1234567890",
    )
    short_failure = [
        v for v in violations if v.principle == Principle.SOLVE_CURRENT_FAILURES
    ]
    assert len(short_failure) == 0


def test_validate_proposal_transaction_currency_only() -> None:
    """Test that currency without amount doesn't pass the ground in reality check."""
    violations = validate_proposal(
        "Use a credit system",
        concrete_failure="problem exists",
        transaction_currency="USD",
    )
    # Currency without amount should still trigger
    credit = [v for v in violations if v.principle == Principle.GROUND_IN_REALITY]
    assert len(credit) > 0


def test_validate_proposal_transaction_amount_only() -> None:
    """Test that amount without currency doesn't pass the ground in reality check."""
    violations = validate_proposal(
        "Use a credit system",
        concrete_failure="problem exists",
        transaction_amount=100.0,
    )
    # Amount without currency should still trigger
    credit = [v for v in violations if v.principle == Principle.GROUND_IN_REALITY]
    assert len(credit) > 0


def test_validate_proposal_all_validating() -> None:
    """Test that all valid elements together pass."""
    violations = validate_proposal(
        "Add logging system to save debug info when app crashes, making debugging easier",
        concrete_failure="Debug info is lost when app crashes, making debugging impossible",
        transaction_amount=500.0,
        transaction_currency="USD",
    )
    assert len(violations) == 0


def test_validate_proposal_speculative_language_with_long_failure() -> None:
    """Test that 'future when' language is detected even with valid failure."""
    # Concrete failure is > 10 chars, but proposal still has speculative language
    violations = validate_proposal(
        "Add logging for when we need telemetry in the future",
        concrete_failure="We lose debug info when crashes happen, making debugging impossible",
    )
    # Should detect speculative language (the "when" + "future" pattern)
    speculative = [
        v for v in violations if v.principle == Principle.SOLVE_CURRENT_FAILURES
    ]
    assert len(speculative) > 0


def test_validate_proposal_only_future_when_speculative() -> None:
    """Test that 'when' + 'future' alone is detected."""
    violations = validate_proposal(
        "Add logging for when we need this in the future",
        concrete_failure="Current system loses data when crashes occur",
    )
    # Should detect the "when we need" pattern
    speculative = [
        v for v in violations if v.principle == Principle.SOLVE_CURRENT_FAILURES
    ]
    assert len(speculative) > 0


def test_validate_proposal_only_future_when_pattern() -> None:
    """Test that 'when' + 'future' is detected."""
    violations = validate_proposal(
        "We need to add this when we scale in the future",
        concrete_failure="Current system is too slow",
    )
    speculative = [
        v for v in violations if v.principle == Principle.SOLVE_CURRENT_FAILURES
    ]
    assert len(speculative) > 0
