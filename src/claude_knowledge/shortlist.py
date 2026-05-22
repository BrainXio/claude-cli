"""Shortlist management for prototype ingestion."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_knowledge._config import get_knowledge_dir


def get_shortlist(
    shortlist_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Load a previously generated shortlist.

    Args:
        shortlist_path: Path to the shortlist JSON. Defaults to
            ~/.claude/data/shortlist.json for backward compatibility.

    Returns:
        List of prototype dicts.
    """
    if shortlist_path is None:
        shortlist_path = get_knowledge_dir() / "shortlist.json"
    path = Path(shortlist_path)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        if isinstance(data, list):
            return data
        # Handle {"prototypes": [...]} format
        if isinstance(data, dict) and "prototypes" in data:
            prototypes = data["prototypes"]
            return prototypes if isinstance(prototypes, list) else []
        # Non-list, non-dict with prototypes key - return empty
        return []
    except (OSError, json.JSONDecodeError):
        return []


def update_shortlist(
    prototypes: list[dict[str, Any]],
    shortlist_path: str | Path | None = None,
) -> Path:
    """Write a new shortlist, replacing any existing one.

    Returns:
        The path written to.
    """
    if shortlist_path is None:
        shortlist_path = get_knowledge_dir() / "shortlist.json"
    path = Path(shortlist_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(prototypes, indent=2) + "\n")
    return path
