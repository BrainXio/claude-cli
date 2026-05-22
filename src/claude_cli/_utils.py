"""Shared utilities for claude_cli."""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, cast


def extract_conversation_context(
    transcript_path: Path, max_turns: int = 30, max_chars: int = 15000
) -> tuple[str, int]:
    """Read JSONL transcript and extract recent turns as markdown."""
    turns: list[str] = []

    with open(transcript_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg = (
                entry.get("message", {})
                if isinstance(entry.get("message"), dict)
                else entry
            )
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role not in ("user", "assistant"):
                continue

            if isinstance(content, list):
                text_parts = [
                    b.get("text", "") if isinstance(b, dict) else str(b)
                    for b in content
                ]
                content = "\n".join(text_parts)

            if isinstance(content, str) and content.strip():
                label = "User" if role == "user" else "Assistant"
                turns.append(f"**{label}:** {content.strip()}\n")

    recent = turns[-max_turns:]
    context = "\n".join(recent)

    if len(context) > max_chars:
        context = context[-max_chars:]
        boundary = context.find("\n**")
        if boundary > 0:
            context = context[boundary + 1 :]

    return context, len(recent)


def parse_stdin_json() -> dict[str, object] | None:
    """Parse JSON from stdin; return None on failure."""
    raw = sys.stdin.read()
    try:
        return cast(dict[str, object], json.loads(raw))
    except json.JSONDecodeError as e:
        logging.error("Failed to parse stdin JSON: %s", e)
        return None


def spawn_detached(
    cmd: list[str],
    log_path: Path | None = None,
    cwd: str | None = None,
) -> None:
    """Spawn a background process, detached from the parent session."""
    kwargs: dict[str, Any] = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    else:
        kwargs["start_new_session"] = True

    if log_path:
        with open(str(log_path), "a") as fh:
            subprocess.Popen(
                cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=cwd, **kwargs
            )
    else:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=cwd,
            **kwargs,
        )
