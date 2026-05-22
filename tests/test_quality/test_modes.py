"""Tests for claude_quality.modes."""

from claude_quality.modes import Mode, get_mode, get_mode_thresholds, set_mode


def test_get_mode_default() -> None:
    assert get_mode() == Mode.DEVELOPER


def test_set_and_get_mode() -> None:
    set_mode(Mode.RESEARCH)
    assert get_mode() == Mode.RESEARCH
    # restore
    set_mode(Mode.DEVELOPER)


def test_get_mode_thresholds() -> None:
    thresholds = get_mode_thresholds(Mode.REVIEW)
    assert thresholds["quality_gate_strict"] is True
    assert thresholds["allow_auto_format"] is False
