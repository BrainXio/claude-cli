"""Path configuration for claude_cli.

All paths follow the canonical workspace architecture:
  ~/.claude/data/         — Global runtime state (gitignored)
  workspace/.claude/      — Workspace runtime config (gitignored)
  workspace/data/         — Workspace data (gitignored)
    bus/                  — Inter-session bus (inter_session_bus.jsonl)
    daily/                — Daily session logs
    kb/                   — Knowledge base artifacts
  workspace/docs/         — Documentation (tracked)
    plans/                — Planning docs
    decisions/            — ADRs
    reports/              — Session reports
    instructions/         — Handoff notes
  workspace/packages/     — Shared libraries
  workspace/infra/        — CI/CD and deployment
  workspace/experiments/  — POC repos (not tracked)
"""

import os
from datetime import datetime
from pathlib import Path


def _resolve(key: str, default: str) -> Path:
    return Path(os.environ.get(key, default)).expanduser().resolve()


# Global runtime state (~/.claude/data/)
DATA_DIR = Path.home() / ".claude" / "data"
STATE_FILE = DATA_DIR / "state.json"


# Workspace root resolution (find .git or use cwd)
def _find_workspace_root() -> Path:
    """Find workspace root by locating .git directory."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".git").exists():
            return parent
    return cwd


WORKSPACE_ROOT = _find_workspace_root()

# Workspace-local data (workspace/data/)
WORKSPACE_DATA = WORKSPACE_ROOT / "data"
DAILY_DIR = _resolve("CLAUDE_DAILY_DIR", str(WORKSPACE_DATA / "daily"))
KNOWLEDGE_DIR = _resolve("CLAUDE_KNOWLEDGE_DIR", str(WORKSPACE_DATA / "kb"))
BUS_DIR = _resolve("CLAUDE_BUS_DIR", str(WORKSPACE_DATA / "bus"))
INTER_SESSION_BUS = BUS_DIR / "inter_session_bus.jsonl"

# Workspace docs (workspace/docs/)
DOCS_DIR = WORKSPACE_ROOT / "docs"
REPORTS_DIR = DOCS_DIR / "reports"
PLANS_DIR = DOCS_DIR / "plans"
INSTRUCTIONS_DIR = DOCS_DIR / "instructions"
DECISIONS_DIR = DOCS_DIR / "decisions"

# Legacy paths for backward compat
INDEX_FILE = KNOWLEDGE_DIR / "index.md"
REPORTS_LOGS = REPORTS_DIR / "logs"
REPORTS_STATE = REPORTS_DIR / "state"
REPORTS_TMP = REPORTS_DIR / "tmp"
ROOT_DIR = Path("~/.claude").expanduser().resolve()


def get_allowed_repos() -> set[str]:
    env = os.environ.get("CLAUDE_ALLOWED_REPOS", "").strip()
    if env:
        return {r.strip() for r in env.split(",") if r.strip()}
    return set()  # safe default


def now() -> datetime:
    return datetime.now().astimezone()


def today_iso() -> str:
    return now().strftime("%Y-%m-%d")
