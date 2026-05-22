"""Path configuration for claude_cli.

All paths follow the canonical workspace architecture:
  ~/.claude/data/
    state.json  — Bootstrap session state
    daily/      — Daily session logs (C.P.R. Compact output)
    knowledge/  — Knowledge base index and categories (C.P.R. Protect output)
    reports/
      logs/     — Hook execution logs
      state/    — Flush state tracking (last-flush.json)
      tmp/      — Temporary flush staging files (cleaned after use)
"""

import os
from datetime import datetime
from pathlib import Path


def _resolve(key: str, default: str) -> Path:
    return Path(os.environ.get(key, default)).expanduser().resolve()


DATA_DIR = Path.home() / ".claude" / "data"
STATE_FILE = DATA_DIR / "state.json"
DAILY_DIR = _resolve("CLAUDE_DAILY_DIR", str(DATA_DIR / "daily"))
KNOWLEDGE_DIR = _resolve("CLAUDE_KNOWLEDGE_DIR", str(DATA_DIR / "knowledge"))
INDEX_FILE = KNOWLEDGE_DIR / "index.md"
REPORTS_DIR = _resolve("CLAUDE_REPORTS_DIR", str(DATA_DIR / "reports"))
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
