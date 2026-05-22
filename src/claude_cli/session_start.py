"""
SessionStart hook - injects knowledge base context into every new session.
"""

import json

from ._config import DAILY_DIR, INDEX_FILE, now, today_iso

MAX_CONTEXT_CHARS = 20_000
MAX_LOG_LINES = 30


def get_recent_log() -> str:
    log_path = DAILY_DIR / f"{today_iso()}.md"
    if not log_path.exists():
        # Try yesterday
        from datetime import timedelta

        yesterday = now() - timedelta(days=1)
        log_path = DAILY_DIR / f"{yesterday.strftime('%Y-%m-%d')}.md"
        if not log_path.exists():
            return "(no recent daily log)"

    lines = log_path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[-MAX_LOG_LINES:])


def _truncate_at_boundary(text: str, max_len: int) -> str:
    """Truncate text at the last paragraph boundary before max_len."""
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_boundary = truncated.rfind("\n\n")
    if last_boundary > max_len * 0.8:
        return truncated[:last_boundary] + "\n\n...(truncated)"
    return truncated + "\n\n...(truncated)"


def build_context() -> str:
    parts = [f"## Today\n{now().strftime('%A, %B %d, %Y')}"]

    if INDEX_FILE.exists():
        parts.append(
            f"## Knowledge Base Index\n\n{INDEX_FILE.read_text(encoding='utf-8')}"
        )
    else:
        parts.append("## Knowledge Base Index\n\n(empty - run compile.py first)")

    parts.append(f"## Recent Daily Log\n\n{get_recent_log()}")

    context = "\n\n---\n\n".join(parts)
    return _truncate_at_boundary(context, MAX_CONTEXT_CHARS)


def main() -> None:
    context = build_context()
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
    exit(0)
