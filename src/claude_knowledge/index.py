"""Search index cache management."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from claude_knowledge._config import get_knowledge_dir


def _compute_corpus_hash(documents: list[tuple[str, str]]) -> str:
    """Compute a stable hash for the entire document corpus."""
    hasher = hashlib.sha256()
    for name, content in sorted(documents):
        hasher.update(name.encode())
        hasher.update(content.encode())
    return hasher.hexdigest()[:16]


def build_index(
    documents: list[tuple[str, str]],
    index_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build and persist a TF-IDF search index.

    Args:
        documents: List of (name, content) tuples.
        index_path: Where to write the index. Defaults to KNOWLEDGE_DIR / index_cache.json.

    Returns:
        The built index dict.
    """
    if index_path is None:
        index_path = get_knowledge_dir() / "index_cache.json"
    path = Path(index_path)

    from claude_knowledge._utils import _compute_tf_idf

    vectors, idf = _compute_tf_idf(documents)
    corpus_hash = _compute_corpus_hash(documents)

    index: dict[str, Any] = {
        "version": 1,
        "corpus_hash": corpus_hash,
        "document_count": len(documents),
        "idf": idf,
        "vectors": vectors,
        "built_at": __import__("datetime").datetime.now().isoformat(),
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2) + "\n")
    return index


def load_index(
    index_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """Load a previously built index.

    Returns:
        Index dict, or None if the index file does not exist.
    """
    if index_path is None:
        index_path = get_knowledge_dir() / "index_cache.json"
    path = Path(index_path)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())  # type: ignore[no-any-return]
    except (OSError, json.JSONDecodeError):
        return None


def index_is_stale(
    documents: list[tuple[str, str]],
    index_path: str | Path | None = None,
) -> bool:
    """Check if the current index is stale relative to the document corpus.

    Returns:
        True if the index needs rebuilding, False if it is up-to-date.
    """
    index = load_index(index_path)
    if index is None:
        return True
    current_hash = _compute_corpus_hash(documents)
    return index.get("corpus_hash") != current_hash
