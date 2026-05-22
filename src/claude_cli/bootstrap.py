"""Claude Code agent bootstrap — minimal environment setup.

Handles: session identity, directory creation, docs sync.
"""

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ._config import DATA_DIR, STATE_FILE, REPORTS_LOGS, REPORTS_STATE, REPORTS_TMP


def _find_git_root() -> Path | None:
    """Return the git repo root if inside one."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass
    return None


def _sync_docs() -> None:
    """Sync workspace .agents/docs to ~/.claude/docs if available."""
    import shutil

    target = Path.home() / ".claude" / "docs"
    target.mkdir(parents=True, exist_ok=True)

    # Try current git repo, then walk up parents looking for .agents/docs
    candidates: list[Path] = []
    git_top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if git_top.returncode == 0:
        candidates.append(Path(git_top.stdout.strip()))

    cwd = Path.cwd()
    candidates.append(cwd)
    for parent in cwd.parents:
        candidates.append(parent)
        if (parent / ".gitmodules").exists():
            break

    source: Path | None = None
    for candidate in candidates:
        potential = candidate / ".agents" / "docs"
        if potential.is_dir():
            source = potential
            break

    if source is None:
        return

    for item in source.iterdir():
        dest = target / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    print(f"Synced docs from {source} to {target}")


def _ensure_guardian(
    model: str = "granite-guardian:latest", timeout: int = 120
) -> None:
    """Pull Granite Guardian if Ollama is available. Non-fatal on failure."""
    try:
        result = subprocess.run(
            ["ollama", "pull", model],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            print(f"  Security model ready: {model}")
        else:
            print(f"  Warning: could not pull {model}: {result.stderr.strip()}")
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        pass  # Ollama not installed or not running


def _sweep_temp_files(max_age_hours: int = 24) -> None:
    """Remove orphaned temp context files older than max_age_hours."""
    tmp = REPORTS_TMP
    if not tmp.is_dir():
        return
    cutoff = datetime.now(timezone.utc).timestamp() - max_age_hours * 3600
    for f in tmp.glob("session-flush-*.md"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
        except OSError:
            pass


def main() -> None:
    print("Bootstrapping Claude Code agent environment...\n")

    agent_name = os.environ.get("CLAUDE_AGENT_NAME", "general")
    task = os.environ.get("CLAUDE_AGENT_TASK")
    branch = os.environ.get("CLAUDE_AGENT_BRANCH", "main")
    worktree = os.environ.get("CLAUDE_AGENT_WORKTREE")

    from ._bootstrap_identity import register_and_resume, handle_batch

    session_record, resumed_items, migrated_tasks = register_and_resume(
        agent_name=agent_name,
        task=task,
        branch=branch,
        worktree=worktree,
    )

    if resumed_items:
        print("\n[Work Queue] Resuming from previous sessions:")
        for item in resumed_items:
            print(item)
        if migrated_tasks:
            print(f"\n  → Migrated {migrated_tasks} tasks to current session.")
        print("\n  Active work items:", session_record["work_items"])

    # Batch session execution
    batch_id = os.environ.get("CLAUDE_BATCH_ID")
    if batch_id:
        session_record = handle_batch(batch_id, session_record)

    # State persistence
    state = {
        "version": 1,
        "session_slug": None,
        "agent_id": session_record["agent_id"],
        "session_id": session_record["session_id"],
        "mode": {
            "string": os.environ.get("CLAUDE_MODE", "developer"),
        },
        "paths": {
            "planning": str(DATA_DIR / "planning"),
            "tasks": str(DATA_DIR / "tasks"),
            "worktrees": str(DATA_DIR / "worktrees"),
        },
        "docs": {
            "path": str(Path.home() / ".claude" / "docs"),
        },
        "last": None,
        "meta": {
            "bootstrapped_at": datetime.now(timezone.utc).isoformat(),
            "bootstrap_source": "hook",
            "identity_version": "1.0",
        },
    }

    for d in (
        DATA_DIR,
        DATA_DIR / "daily",
        DATA_DIR / "knowledge",
        REPORTS_LOGS,
        REPORTS_STATE,
        REPORTS_TMP,
    ):
        d.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")
    print(f"State persisted to {STATE_FILE}")

    _ensure_guardian()
    _sweep_temp_files()
    _sync_docs()

    print("\nBootstrap complete.")


if __name__ == "__main__":
    main()
