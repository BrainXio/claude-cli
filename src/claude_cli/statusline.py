#!/usr/bin/env python3
"""Status line generator for Claude Code.

Reads JSON from stdin (Claude Code context object), outputs a formatted
status line with model name and context usage bar.

Configured in settings.json:
    "statusLine": {
        "type": "command",
        "command": "python3 ${workspaceFolder}/claude-cli/bin/statusline.py"
    }
"""

import json
import sys

from claude_cli._hook_metrics import timed_hook


def build_bar(percentage: int, width: int = 10) -> str:
    """Build an ASCII progress bar."""
    filled = percentage * width // 100
    empty = width - filled
    return "#" * filled + "-" * empty


def color_for_usage(percentage: int) -> str:
    """Return ANSI color code based on usage percentage."""
    if percentage < 50:
        return "\033[32m"  # green
    elif percentage < 80:
        return "\033[33m"  # yellow
    elif percentage < 90:
        return "\033[38;5;208m"  # orange
    else:
        return "\033[31m"  # red


def main() -> None:
    with timed_hook("statusline"):
        try:
            data = json.load(sys.stdin)
        except (json.JSONDecodeError, EOFError):
            return

        model = data.get("model", {}).get("display_name", "unknown")
        used = data.get("context_window", {}).get("used_percentage")

        cyan = "\033[01;36m"
        reset = "\033[00m"

        if used is not None:
            used_int = int(used)
            bar = build_bar(used_int)
            color = color_for_usage(used_int)
            print(f"{cyan}{model}{reset} {color}[{bar}]{reset} {used_int}%")
        else:
            print(f"{cyan}{model}{reset}")


if __name__ == "__main__":
    main()
