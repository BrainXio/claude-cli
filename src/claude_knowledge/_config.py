"""Path constants and configuration for the personal knowledge base."""

import os
import warnings
from datetime import UTC, datetime
from pathlib import Path


def _find_root_dir() -> Path:
    """Robustly locate the project root directory."""

    # 1. Environment variable override (highest priority)
    if root_env := os.getenv("PKB_ROOT"):
        return Path(root_env).expanduser().resolve()

    # 2. Sentinel file detection
    current = Path(__file__).resolve().parent
    for _ in range(10):
        for sentinel in [
            ".project-root",
            "pyproject.toml",
            ".git",
            "README.md",
            "LICENSE",
        ]:
            if (current / sentinel).exists():
                return current
        current = current.parent

    # 3. Fallback
    fallback = Path(__file__).resolve().parent.parent
    warnings.warn(
        f"Could not detect project root via sentinel. Falling back to: {fallback}\n"
        f"Recommended: create a .project-root file in your actual root.",
        stacklevel=2,
    )
    return fallback


# ── Base Directories ───────────────────────────────────────────────────

ROOT_DIR = _find_root_dir()

# Agent/tools directory (now contains scripts + former hooks)
AGENT_DIR = Path(os.getenv("PKB_AGENT_DIR", "~/.claude")).expanduser().resolve()

# ── Project Content Directories ───────────────────────────────────────
# Output directories at user's home (~), not under ~/.claude
DAILY_DIR = Path("~/daily").expanduser().resolve()
KNOWLEDGE_DIR = Path("~/knowledge-base").expanduser().resolve()
CONCEPTS_DIR = KNOWLEDGE_DIR / "concepts"
CONNECTIONS_DIR = KNOWLEDGE_DIR / "connections"
QA_DIR = KNOWLEDGE_DIR / "qa"
REPORTS_DIR = Path("~/reports").expanduser().resolve()

# ── Tool Directories (all now under scripts/) ─────────────────────────
SCRIPTS_DIR = AGENT_DIR / "scripts"
AGENTS_FILE = AGENT_DIR / "AGENTS.md"

# ── Reports subdirectories (all metadata/logs/state live here) ────────
REPORTS_LOGS = REPORTS_DIR / "logs"
REPORTS_STATE = REPORTS_DIR / "state"
REPORTS_TMP = REPORTS_DIR / "tmp"

# ── Key Files ──────────────────────────────────────────────────────────
INDEX_FILE = KNOWLEDGE_DIR / "index.md"
LOG_FILE = KNOWLEDGE_DIR / "log.md"
STATE_FILE = REPORTS_STATE / "state.json"

# ── Time Configuration ─────────────────────────────────────────────────
USE_UTC: bool = False  # Use local time for daily log alignment


def now() -> datetime:
    """Current time (UTC or local based on USE_UTC)."""
    return datetime.now(UTC) if USE_UTC else datetime.now().astimezone()


def now_iso() -> str:
    """Current time in ISO 8601 format."""
    return now().isoformat(timespec="seconds")


def today_iso() -> str:
    """Current date in YYYY-MM-DD."""
    return now().strftime("%Y-%m-%d")


# ── Helpers ────────────────────────────────────────────────────────────
def ensure_dirs() -> None:
    """Create required directories. Skipped for hooks for performance."""
    if os.getenv("PKB_SKIP_ENSURE_DIRS") == "1":
        return

    for directory in (
        DAILY_DIR,
        KNOWLEDGE_DIR,
        CONCEPTS_DIR,
        CONNECTIONS_DIR,
        QA_DIR,
        REPORTS_DIR,
        REPORTS_LOGS,
        REPORTS_STATE,
        REPORTS_TMP,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def print_config_summary() -> None:
    """Helpful debug function."""
    print(f"ROOT_DIR       → {ROOT_DIR}")
    print(f"AGENT_DIR      → {AGENT_DIR}")
    print(f"KNOWLEDGE_DIR  → {KNOWLEDGE_DIR}")
    print(f"SCRIPTS_DIR    → {SCRIPTS_DIR}")
    print(f"USE_UTC        → {USE_UTC}")


# ── Auto-initialization ────────────────────────────────────────────────
# Skip heavy operations when running inside hooks
if os.getenv("CLAUDE_INVOKED_BY") is None and os.getenv("PKB_SKIP_ENSURE_DIRS") != "1":
    ensure_dirs()
