#!/usr/bin/env python3
"""Standards guard: blocks manifesto content, phantom links, and philosophy in standards docs.

Claude Code PreToolUse hook for Edit and Write tools.
Receives JSON on stdin, checks new content for forbidden patterns.
Exit 0 with JSON output to deny; exit 0 with no output to allow.
"""

import json
import re
import sys

from claude_cli._config import get_allowed_repos
from claude_cli._hook_metrics import timed_hook

# --- Forbidden patterns ---

PHILOSOPHY_SLUDGE = [
    (
        r"local[\s-]?first",
        "philosophy sludge: 'local-first' is forbidden in standards docs",
    ),
    (r"quiet\s+joy", "philosophy sludge: 'quiet joy' is forbidden in standards docs"),
    (
        r"[Cc]ore\s+approval",
        "philosophy sludge: 'Core approval' tiers are forbidden in standards docs",
    ),
    (r"\bsacred\b", "philosophy sludge: 'sacred' is forbidden in standards docs"),
    (
        r"[Aa]nother\s+[Ii]ntelligence",
        "philosophy sludge: 'Another Intelligence' is forbidden in standards docs",
    ),
    (
        r"sovereign\s+[Aa][Ig]",
        "philosophy sludge: 'sovereign AI/agent' is forbidden in standards docs",
    ),
    (
        r"fun\*\*ctional",
        "philosophy sludge: 'fun**ctional' is forbidden in standards docs",
    ),
    (
        r"becoming\s+a\s+proper\s+idiot",
        "philosophy sludge: 'becoming a proper idiot' is forbidden in standards docs",
    ),
    (
        r"restless\s+mirror\s+of\s+curiosity",
        "philosophy sludge: 'restless mirror of curiosity' is forbidden in standards docs",
    ),
]

MANIFESTO_TONE = [
    (
        r"is\s+the\s+(\*{1,2})?only(\*{1,2})?\s+allowed",
        "manifesto tone: 'is the only allowed' — use neutral language instead",
    ),
    (
        r"managed\s+exclusively\s+through",
        "manifesto tone: 'managed exclusively through' — use neutral language instead",
    ),
]

PHANTOM_REPO_RE = re.compile(
    r"https?://github\.com/([^\s\)\]/]+/[^\s\)\]]+)", re.IGNORECASE
)

# --- Guarded file patterns ---

GUARDED_SUFFIXES = (
    ".github/README.md",
    "/README.md",  # broad but only triggers for .github context
    "CONTRIBUTING.md",
    "SECURITY.md",
)


def is_guarded_path(file_path: str) -> bool:
    lower = file_path.lower()
    return any(lower.endswith(s.lower()) for s in GUARDED_SUFFIXES)


def is_workflow_file(file_path: str) -> bool:
    lower = file_path.lower()
    return lower.endswith((".yml", ".yaml")) and ".github" in lower


def check_content(content: str, file_path: str) -> list[str]:
    violations = []
    lines = content.split("\n")

    # Philosophy sludge
    for pattern, reason in PHILOSOPHY_SLUDGE:
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                violations.append(f"L{i}: {reason} — found: '{line.strip()}'")

    # Manifesto tone
    for pattern, reason in MANIFESTO_TONE:
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                violations.append(f"L{i}: {reason} — found: '{line.strip()}'")

    # Phantom repo links
    allowed = get_allowed_repos()
    for i, line in enumerate(lines, 1):
        for match in PHANTOM_REPO_RE.finditer(line):
            repo = match.group(1)
            if repo not in allowed:
                violations.append(
                    f"L{i}: phantom repo link: '{repo}' — not in verified repo list"
                )

    return violations


def check_workflow_content(content: str, file_path: str) -> list[str]:
    violations = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Floating tags
        if re.search(r"@\b(latest|stable)\b", stripped) and "github.com" in stripped:
            violations.append(
                f"L{i}: floating tag detected: use SHA pinning instead — found: '{stripped}'"
            )
        # curl|sudo / curl|bash
        if re.search(r"curl\b.*\|\s*(sudo|bash|sh)", stripped):
            violations.append(
                f"L{i}: curl|sudo/bash pattern — supply chain risk — found: '{stripped}'"
            )

    return violations


def main() -> None:
    with timed_hook("standards_guard"):
        _run_guard()


def _run_guard() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        return

    # Extract new content
    if tool_name == "Edit":
        content = tool_input.get("new_string", "")
    elif tool_name == "Write":
        content = tool_input.get("content", "")
    else:
        return

    if not content:
        return

    all_violations = []

    if is_guarded_path(file_path):
        all_violations.extend(check_content(content, file_path))

    if is_workflow_file(file_path):
        all_violations.extend(check_workflow_content(content, file_path))

    if all_violations:
        reasons = "; ".join(all_violations[:5])
        if len(all_violations) > 5:
            reasons += f"; ... and {len(all_violations) - 5} more"
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Standards guard: {reasons}",
            }
        }
        print(json.dumps(output))

    return


if __name__ == "__main__":
    main()
