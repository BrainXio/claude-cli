"""Anti-gaming validator: 7 first principles of anti-over-engineering."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Principle(str, Enum):
    GROUND_IN_REALITY = "ground_in_reality"
    SOLVE_CURRENT_FAILURES = "solve_current_failures"
    MEASURE_OUTCOMES = "measure_outcomes"
    NO_ACADEMIC_VALIDATION = "no_academic_validation"
    DESIGN_FOR_CURRENT = "design_for_current"
    TRUST_UPWARD = "trust_upward"
    COMPLEXITY_TAX = "complexity_tax"


@dataclass
class Violation:
    principle: Principle
    reason: str
    line: int | None = None


def validate_proposal(
    description: str,
    concrete_failure: str | None = None,
    transaction_amount: float | None = None,
    transaction_currency: str | None = None,
) -> list[Violation]:
    """Validate a proposal against the 7 anti-over-engineering principles.

    Returns a list of violations. Empty list means the proposal passes.
    """
    violations: list[Violation] = []
    text = description.lower()

    # Principle 1: Ground in physical reality
    if transaction_amount is not None and transaction_currency is not None:
        pass
    else:
        if "credit" in text and "currency" not in text:
            violations.append(
                Violation(
                    principle=Principle.GROUND_IN_REALITY,
                    reason="Credit system without external currency anchor detected.",
                )
            )

    # Principle 2: Solve current failures
    if not concrete_failure or len(concrete_failure) < 10:
        violations.append(
            Violation(
                principle=Principle.SOLVE_CURRENT_FAILURES,
                reason="No concrete, current failure scenario provided.",
            )
        )
    elif "future" in text and "when" in text:
        violations.append(
            Violation(
                principle=Principle.SOLVE_CURRENT_FAILURES,
                reason="Proposal appears speculative ('when we need...', 'future agents...').",
            )
        )

    # Principle 3: Measure outcomes, not activity
    activity_keywords = [
        "posts",
        "attendance",
        "labels generated",
        "meeting count",
        "bus activity",
        "channel messages",
    ]
    for kw in activity_keywords:
        if kw in text:
            violations.append(
                Violation(
                    principle=Principle.MEASURE_OUTCOMES,
                    reason=f"Activity metric detected: '{kw}'. Measure outcomes only.",
                )
            )
            break

    # Principle 4: No academic-validation-seeking
    academic_phrases = [
        "literature says",
        "research shows",
        "paper demonstrates",
        "according to",
        "studies indicate",
    ]
    for phrase in academic_phrases:
        if phrase in text:
            violations.append(
                Violation(
                    principle=Principle.NO_ACADEMIC_VALIDATION,
                    reason=f"Academic citation used as justification: '{phrase}'.",
                )
            )
            break

    # Principle 5: Design for current capabilities
    capability_gaps = [
        "when agents can reflect",
        "once llm-as-judge is deployed",
        "future capability",
        "when we have",
    ]
    for gap in capability_gaps:
        if gap in text:
            violations.append(
                Violation(
                    principle=Principle.DESIGN_FOR_CURRENT,
                    reason=f"Design assumes future capability: '{gap}'.",
                )
            )
            break

    # Principle 6: Trust upward
    penalty_keywords = [
        "strike",
        "penalty",
        "punish",
        "negligence multiplier",
        "error cost",
        "reputation score",
        "adversarial audit",
    ]
    for kw in penalty_keywords:
        if kw in text:
            violations.append(
                Violation(
                    principle=Principle.TRUST_UPWARD,
                    reason=f"Penalty-based mechanism detected: '{kw}'. Use progressive trust instead.",
                )
            )
            break

    # Principle 7: Complexity tax
    if "we'll figure out" in text or "maintenance later" in text:
        violations.append(
            Violation(
                principle=Principle.COMPLEXITY_TAX,
                reason="Maintenance burden deferred ('we'll figure out later').",
            )
        )

    return violations
