"""Operational mode management for quality gates."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any


class Mode(str, Enum):
    DEVELOPER = "developer"
    RESEARCH = "research"
    REVIEW = "review"
    OPS = "ops"
    PERSONAL = "personal"


_MODE_THRESHOLDS: dict[Mode, dict[str, Any]] = {
    Mode.DEVELOPER: {
        "description": "Standard gates for active development",
        "quality_gate_strict": True,
        "allow_auto_format": True,
        "max_complexity": 10,
    },
    Mode.RESEARCH: {
        "description": "Lenient gates for exploratory research",
        "quality_gate_strict": False,
        "allow_auto_format": True,
        "max_complexity": 20,
    },
    Mode.REVIEW: {
        "description": "Strict gates for formal review",
        "quality_gate_strict": True,
        "allow_auto_format": False,
        "max_complexity": 8,
    },
    Mode.OPS: {
        "description": "Focused on operational content",
        "quality_gate_strict": True,
        "allow_auto_format": True,
        "max_complexity": 12,
    },
    Mode.PERSONAL: {
        "description": "Permissive gates for personal notes",
        "quality_gate_strict": False,
        "allow_auto_format": True,
        "max_complexity": 30,
    },
}

_STATE_FILE = Path.home() / ".claude" / "mode_state.json"


def get_mode() -> Mode:
    """Return the current operational mode."""
    if _STATE_FILE.exists():
        import json

        try:
            data = json.loads(_STATE_FILE.read_text())
            raw = data.get("mode", Mode.DEVELOPER.value)
            return Mode(raw)
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    return Mode.DEVELOPER


def set_mode(mode: Mode) -> None:
    """Set the current operational mode."""
    import json

    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {"mode": mode.value, "thresholds": _MODE_THRESHOLDS[mode]}
    _STATE_FILE.write_text(json.dumps(data, indent=2) + "\n")


def get_mode_thresholds(mode: Mode | None = None) -> dict[str, Any]:
    """Return thresholds for a given mode (or current mode if None)."""
    target = mode or get_mode()
    return _MODE_THRESHOLDS[target]
