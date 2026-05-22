"""Raw markdown ingestion into tracked artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from claude_knowledge._config import KNOWLEDGE_DIR, now_iso


def _file_hash(path: Path) -> str:
    """Compute a stable hash for a file's content."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown. Returns (meta, body)."""
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    try:
        import yaml

        meta = yaml.safe_load(parts[1])
        if not isinstance(meta, dict):
            meta = {}
        return meta, parts[2]
    except ImportError:
        return {}, content


def ingest_dir(
    source: str | Path,
    *,
    dry_run: bool = False,
    force_all: bool = False,
) -> dict[str, Any]:
    """Ingest all markdown files under source into the knowledge base.

    Returns:
        {"ingested": int, "unchanged": int, "errors": list[str]}
    """
    src = Path(source).resolve()
    state_file = KNOWLEDGE_DIR / "ingest_state.json"
    state: dict[str, Any] = {}
    if state_file.exists() and not force_all:
        try:
            state = json.loads(state_file.read_text())
        except (OSError, json.JSONDecodeError):
            state = {}

    ingested = 0
    unchanged = 0
    errors: list[str] = []

    for path in src.rglob("*.md"):
        try:
            h = _file_hash(path)
            rel = str(path.relative_to(src))
            if not force_all and state.get(rel) == h:
                unchanged += 1
                continue

            content = path.read_text()
            meta, body = _parse_frontmatter(content)

            # Write artifact
            artifact_dir = KNOWLEDGE_DIR / "artifacts"
            artifact_dir.mkdir(parents=True, exist_ok=True)
            artifact = artifact_dir / f"{rel.replace('/', '_')}.json"
            artifact.write_text(
                json.dumps(
                    {
                        "source": str(path),
                        "meta": meta,
                        "body": body,
                        "ingested_at": now_iso(),
                        "hash": h,
                    },
                    indent=2,
                )
                + "\n"
            )

            state[rel] = h
            ingested += 1
        except OSError as e:
            errors.append(f"{path}: {e}")

    if not dry_run:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, indent=2) + "\n")

    return {"ingested": ingested, "unchanged": unchanged, "errors": errors}
