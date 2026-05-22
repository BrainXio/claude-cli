"""
PreCompact hook - captures conversation transcript before auto-compaction.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

# Prevent ensure_dirs() from running inside hooks
os.environ["PKB_SKIP_ENSURE_DIRS"] = "1"

from ._config import ROOT_DIR, REPORTS_LOGS, REPORTS_TMP, now
from ._utils import extract_conversation_context, parse_stdin_json, spawn_detached

logging.basicConfig(
    filename=str(REPORTS_LOGS / "flush.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [pre-compact] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

MIN_TURNS_TO_FLUSH = 5


def main() -> None:
    hook_input = parse_stdin_json()
    if hook_input is None:
        return

    session_id = hook_input.get("session_id", "unknown")
    transcript_path_str = hook_input.get("transcript_path", "")

    logging.info("PreCompact fired: session=%s", session_id)

    if not transcript_path_str or not isinstance(transcript_path_str, str):
        logging.info("SKIP: no transcript path")
        return

    if not isinstance(session_id, str):
        logging.info("SKIP: invalid session_id")
        return

    transcript_path = Path(transcript_path_str)
    if not transcript_path.exists():
        logging.info("SKIP: transcript missing: %s", transcript_path_str)
        return

    try:
        context, turn_count = extract_conversation_context(transcript_path)
    except Exception as e:
        logging.error("Context extraction failed: %s", e)
        return

    if not context.strip() or turn_count < MIN_TURNS_TO_FLUSH:
        logging.info("SKIP: empty context or too few turns (%d)", turn_count)
        return

    timestamp = now().strftime("%Y%m%d-%H%M%S")
    context_file = REPORTS_TMP / f"flush-context-{session_id}-{timestamp}.md"
    REPORTS_TMP.mkdir(parents=True, exist_ok=True)
    context_file.write_text(context, encoding="utf-8")

    flush_script = ROOT_DIR / "scripts" / "flush.py"
    cmd = [
        "uv",
        "run",
        "--directory",
        str(ROOT_DIR),
        "python",
        str(flush_script),
        str(context_file),
        session_id,
    ]

    spawn_detached(cmd, cwd=str(ROOT_DIR))
    logging.info(
        "Spawned flush.py for session %s (%d turns, %d chars)",
        session_id,
        turn_count,
        len(context),
    )


if __name__ == "__main__":
    main()
