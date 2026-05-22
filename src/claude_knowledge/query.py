"""TF-IDF semantic search over the knowledge base."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from claude_knowledge._config import KNOWLEDGE_DIR
from claude_knowledge._utils import _compute_tf_idf, _tokenize


def _cosine_similarity(
    vec1: dict[str, float],
    vec2: dict[str, float],
) -> float:
    """Compute cosine similarity between two sparse vectors."""
    terms = set(vec1) & set(vec2)
    if not terms:
        return 0.0
    dot = sum(vec1[t] * vec2[t] for t in terms)
    norm1 = math.sqrt(sum(v**2 for v in vec1.values()))
    norm2 = math.sqrt(sum(v**2 for v in vec2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def query_kb(
    question: str,
    *,
    top_k: int = 5,
    min_version: int | None = None,
    max_version: int | None = None,
) -> list[dict[str, Any]]:
    """Query the knowledge base using TF-IDF semantic search.

    Args:
        question: Natural language search query.
        top_k: Maximum number of results to return.
        min_version: Optional minimum source version filter.
        max_version: Optional maximum source version filter.

    Returns:
        List of result dicts with "source", "score", and "excerpt" keys.
    """
    articles_dir = KNOWLEDGE_DIR / "articles"
    if not articles_dir.exists():
        return []

    # Load all articles
    documents: list[tuple[str, str]] = []
    for path in articles_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text())
            content = json.dumps(data)
            documents.append((str(path), content))
        except (OSError, json.JSONDecodeError):
            continue

    if not documents:
        return []

    # Compute TF-IDF
    vectors, _ = _compute_tf_idf(documents)

    # Compute query vector
    from collections import Counter

    query_tokens = _tokenize(question)
    query_tf = Counter(query_tokens)
    query_vec = {
        term: count / max(query_tf.values()) for term, count in query_tf.items()
    }

    # Score all documents
    scores: list[tuple[str, float]] = []
    for name, vec in vectors.items():
        score = _cosine_similarity(query_vec, vec)
        if score > 0:
            scores.append((name, score))

    scores.sort(key=lambda x: x[1], reverse=True)

    results: list[dict[str, Any]] = []
    for source, score in scores[:top_k]:
        # Extract a short excerpt
        try:
            data = json.loads(Path(source).read_text())
            excerpt = json.dumps(data)[:200] + "..."
        except OSError:
            excerpt = ""
        results.append(
            {
                "source": source,
                "score": round(score, 4),
                "excerpt": excerpt,
            }
        )

    return results
