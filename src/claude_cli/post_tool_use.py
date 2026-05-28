#!/usr/bin/env python3
"""PostToolUse hook: detect errors and trigger incident response.

Claude Code PostToolUse hook for error detection and incident response.
Receives JSON on stdin with tool execution results.
Exit 0 always — this is observability, not blocking.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from claude_cli._hook_metrics import timed_hook


def extract_error(data: dict) -> dict | None:
    """Extract error information from tool result."""
    tool_name = data.get("tool_name", "")
    tool_result = data.get("tool_result", {})

    # Check for explicit error field
    if tool_result.get("is_error", False):
        return {
            "tool": tool_name,
            "error": tool_result.get("content", "Unknown error"),
            "error_type": "tool_error",
        }

    # Check for non-zero exit in Bash results
    if tool_name == "Bash":
        exit_code = tool_result.get("exit_code", 0)
        if isinstance(exit_code, int) and exit_code != 0:
            return {
                "tool": "Bash",
                "error": tool_result.get("stderr", tool_result.get("content", "")),
                "error_type": "command_failure",
                "exit_code": exit_code,
            }

    return None


def classify_severity(error: dict) -> str:
    """Classify error severity based on patterns."""
    error_text = (error.get("error", "") or "").lower()

    # SEV1: Data loss, security, prod down
    sev1_patterns = [
        "data loss",
        "security",
        "breach",
        "unauthorized",
        "production",
        "prod down",
        "database corrupted",
        "secret exposed",
        "credential leak",
    ]
    if any(p in error_text for p in sev1_patterns):
        return "SEV1"

    # SEV2: Build broken, tests failing, blocking work
    sev2_patterns = [
        "build failed",
        "test failed",
        "compilation error",
        "type error",
        "import error",
        "syntax error",
        "permission denied",
        "file not found",
        "connection refused",
        "timeout",
    ]
    if any(p in error_text for p in sev2_patterns):
        return "SEV2"

    # SEV3: Everything else (lint, docs, cosmetic)
    return "SEV3"


def find_relevant_mitigations(error: dict, workspace_root: Path) -> list[Path]:
    """Find existing mitigations relevant to this error."""
    mitigations_dir = workspace_root / "docs" / "mitigations"
    if not mitigations_dir.exists():
        return []

    error_text = error.get("error", "") or ""
    tool = error.get("tool", "")
    error_type = error.get("error_type", "")

    relevant = []
    error_words = set(error_text.lower().split())

    for mitigation_file in mitigations_dir.glob("*.md"):
        content = mitigation_file.read_text().lower()
        # Check if error signature or tool matches
        if tool.lower() in content or error_type in content:
            relevant.append(mitigation_file)
            continue
        # Check word overlap
        overlap = len(error_words & set(content.split()))
        if overlap >= 3:  # At least 3 words in common
            relevant.append(mitigation_file)

    return relevant[:5]  # Max 5 mitigations


def post_incident_event(error: dict, severity: str, workspace_root: Path) -> None:
    """Log incident to bus and create task for tracking."""
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Post to bus if SEV1/SEV2
    if severity in ("SEV1", "SEV2"):
        bus_file = workspace_root / "data" / "bus" / "inter_session_bus.jsonl"
        if bus_file.exists():
            msg = {
                "content": f"INCIDENT {severity}: {error.get('tool')} failed — {error.get('error', '')[:100]}",
                "from": "incident-response",
                "to": "all",
                "ts": ts,
                "type": "status",
            }
            with open(bus_file, "a") as f:
                f.write(json.dumps(msg) + "\n")


def generate_mitigation_context(error: dict, relevant_mitigations: list[Path]) -> str:
    """Generate context about relevant mitigations for the agent."""
    if not relevant_mitigations:
        return "No prior mitigations found for this error type."

    context_lines = ["**Relevant mitigations found:**"]
    for mit_path in relevant_mitigations:
        # Read first 10 lines to get error signature
        content = mit_path.read_text().split("\n")[:15]
        context_lines.append(
            f"- `{mit_path}`: {content[0][:100] if content else 'N/A'}"
        )

    return "\n".join(context_lines)


def main() -> None:
    with timed_hook("post_tool_use"):
        _run_hook()


def _run_hook() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return

    # Extract error if present
    error = extract_error(data)
    if not error:
        return  # No error, nothing to do

    # Classify severity
    severity = classify_severity(error)

    # Determine workspace root
    workspace_root = Path(os.getcwd())
    # Walk up to find workspace (has .git or CLAUDE.md)
    for parent in [workspace_root] + list(workspace_root.parents):
        if (parent / ".git").exists() or (parent / "CLAUDE.md").exists():
            workspace_root = parent
            break

    # Find relevant mitigations
    relevant = find_relevant_mitigations(error, workspace_root)

    # Post incident event
    post_incident_event(error, severity, workspace_root)

    # Generate context for next tool use
    mitigation_context = generate_mitigation_context(error, relevant)

    # Write error context to temp file for PreToolUse to read
    error_context_file = workspace_root / ".claude" / "last_error.json"
    error_context_file.parent.mkdir(parents=True, exist_ok=True)

    error_context = {
        "error": error,
        "severity": severity,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "relevant_mitigations": [str(p) for p in relevant],
        "mitigation_context": mitigation_context,
    }
    error_context_file.write_text(json.dumps(error_context, indent=2))

    # For SEV1/SEV2, also write a prompt for incident-response agent
    if severity in ("SEV1", "SEV2"):
        prompt_file = workspace_root / ".claude" / "incident_pending.txt"
        prompt_file.write_text(
            f"INCIDENT {severity} DETECTED\n"
            f"Tool: {error.get('tool')}\n"
            f"Error: {error.get('error', '')[:200]}\n"
            f"Relevant mitigations: {relevant}\n"
            f'Action: /skill incident-response "{error.get("error", "")[:100]}"\n'
        )


if __name__ == "__main__":
    main()
