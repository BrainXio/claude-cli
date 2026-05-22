"""Daily log compilation into structured articles."""

from __future__ import annotations

import json
import re
from typing import Any

from claude_knowledge._config import DAILY_DIR, KNOWLEDGE_DIR, now_iso


def _extract_entries(log_content: str) -> list[dict[str, Any]]:
    """Parse a daily log into structured entries."""
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    lines = log_content.splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Simple heuristic: timestamped lines start new entries
        if re.match(r"^\d{4}-\d{2}-\d{2}[T ]", line):
            if current:
                entries.append(current)
            current = {"timestamp": line.split()[0], "body": line, "tags": []}
        elif current is not None:
            current["body"] += "\n" + line
            # Tag extraction
            for tag in re.findall(r"#\w+", line):
                current["tags"].append(tag.lstrip("#"))

    if current:
        entries.append(current)

    return entries


def compile_logs(
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Compile daily logs into structured KB articles.

    Returns:
        {"compiled": int, "errors": list[str]}
    """
    articles_dir = KNOWLEDGE_DIR / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)

    state_file = KNOWLEDGE_DIR / "compile_state.json"
    state: dict[str, Any] = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
        except (OSError, json.JSONDecodeError):
            state = {}

    compiled = 0
    errors: list[str] = []

    for log_path in DAILY_DIR.glob("*.md"):
        try:
            content = log_path.read_text()
            entries = _extract_entries(content)
            if not entries:
                continue

            date_str = log_path.stem
            article_path = articles_dir / f"{date_str}.json"

            if not dry_run:
                article_path.write_text(
                    json.dumps(
                        {
                            "date": date_str,
                            "entries": entries,
                            "compiled_at": now_iso(),
                        },
                        indent=2,
                    )
                    + "\n"
                )

            state[date_str] = now_iso()
            compiled += 1
        except OSError as e:
            errors.append(f"{log_path}: {e}")

    if not dry_run:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, indent=2) + "\n")

    return {"compiled": compiled, "errors": errors}
