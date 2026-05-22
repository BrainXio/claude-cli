"""Issue precedent recording and checking."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Precedent:
    """A recorded issue pattern that can be checked automatically."""

    check: str
    description: str
    fix: str
    scope: str  # "local", "ci", or "both"
    severity: str  # "info", "warning", "error", "fatal"
    created_at: datetime = field(default_factory=datetime.now)
    hits: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "description": self.description,
            "fix": self.fix,
            "scope": self.scope,
            "severity": self.severity,
            "created_at": self.created_at.isoformat(),
            "hits": self.hits,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Precedent:
        return cls(
            check=data["check"],
            description=data["description"],
            fix=data["fix"],
            scope=data.get("scope", "both"),
            severity=data.get("severity", "warning"),
            created_at=datetime.fromisoformat(data["created_at"]),
            hits=data.get("hits", 0),
        )


_PRECEDENTS_FILE = Path.home() / ".claude" / "precedents.json"


def _load_precedents() -> list[Precedent]:
    """Load all recorded precedents from disk."""
    if not _PRECEDENTS_FILE.exists():
        return []
    import json

    try:
        raw = json.loads(_PRECEDENTS_FILE.read_text())
        return [Precedent.from_dict(p) for p in raw.get("precedents", [])]
    except (OSError, json.JSONDecodeError):
        return []


def _save_precedents(precedents: list[Precedent]) -> None:
    """Save precedents to disk."""
    import json

    _PRECEDENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {"precedents": [p.to_dict() for p in precedents]}
    _PRECEDENTS_FILE.write_text(json.dumps(data, indent=2) + "\n")


def record_issue(
    check: str,
    description: str,
    fix: str,
    scope: str = "both",
    severity: str = "warning",
) -> Precedent:
    """Record a new issue pattern so it can be prevented in future."""
    precedents = _load_precedents()
    precedent = Precedent(
        check=check,
        description=description,
        fix=fix,
        scope=scope,
        severity=severity,
    )
    precedents.append(precedent)
    _save_precedents(precedents)
    return precedent


def check_precedent(
    precedent: Precedent,
    cwd: str | None = None,
) -> tuple[bool, str]:
    """Run a single precedent check. Returns (pass, output)."""
    try:
        result = subprocess.run(
            precedent.check,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=30,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


def run_precedent_checks(scope: str = "both") -> dict[str, list[dict[str, Any]]]:
    """Run all precedent checks for a given scope.

    Returns a dict mapping severity to list of failures.
    """
    precedents = _load_precedents()
    results: dict[str, list[dict[str, Any]]] = {
        "info": [],
        "warning": [],
        "error": [],
        "fatal": [],
    }

    for p in precedents:
        if scope not in (p.scope, "both"):
            continue
        passed, output = check_precedent(p)
        if not passed:
            p.hits += 1
            results[p.severity].append(
                {
                    "description": p.description,
                    "fix": p.fix,
                    "output": output.strip(),
                    "hits": p.hits,
                }
            )

    _save_precedents(precedents)
    return results
