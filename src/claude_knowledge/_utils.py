"""Shared utilities for the claude_knowledge package."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from claude_knowledge import _config


# ── State management ──────────────────────────────────────────────────


def load_state() -> dict[str, Any]:
    """Load persistent state from state.json."""
    if _config.STATE_FILE.exists():
        data: dict[str, Any] = json.loads(
            _config.STATE_FILE.read_text(encoding="utf-8")
        )
        return data
    state: dict[str, Any] = {
        "ingested": {},
        "query_count": 0,
        "last_lint": None,
        "total_cost": 0.0,
    }
    return state


def save_state(state: dict[str, Any]) -> None:
    """Save state to state.json."""
    _config.REPORTS_STATE.mkdir(parents=True, exist_ok=True)
    _config.STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── File hashing ──────────────────────────────────────────────────────


def file_hash(path: Path) -> str:
    """SHA-256 hash of a file (first 16 hex chars)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


# ── Slug / naming ─────────────────────────────────────────────────────


def slugify(text: str) -> str:
    """Convert text to a filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


# ── Wikilink helpers ──────────────────────────────────────────────────


def extract_wikilinks(content: str) -> list[str]:
    """Extract all [[wikilinks]] from markdown content.

    Handles Obsidian-style aliases: [[link|alias]] returns the link target only.
    """
    matches = re.findall(r"\[\[([^\]]+)\]\]", content)
    return [m.split("|")[0].strip() for m in matches]


def wiki_article_exists(link: str) -> bool:
    """Check if a wikilinked article exists on disk."""
    path = _config.KNOWLEDGE_DIR / f"{link}.md"
    return path.exists()


# ── Wiki content helpers ──────────────────────────────────────────────


def read_wiki_index() -> str:
    """Read the knowledge base index file."""
    if _config.INDEX_FILE.exists():
        return _config.INDEX_FILE.read_text(encoding="utf-8")
    return "# Knowledge Base Index\n\n| Article | Summary | Compiled From | Updated |\n|---------|---------|---------------|---------|"


def read_all_wiki_content() -> str:
    """Read index + all wiki articles into a single string for context."""
    parts = [f"## INDEX\n\n{read_wiki_index()}"]

    for subdir in [_config.CONCEPTS_DIR, _config.CONNECTIONS_DIR, _config.QA_DIR]:
        if not subdir.exists():
            continue
        for md_file in sorted(subdir.glob("*.md")):
            rel = md_file.relative_to(_config.KNOWLEDGE_DIR)
            content = md_file.read_text(encoding="utf-8")
            parts.append(f"## {rel}\n\n{content}")

    return "\n\n---\n\n".join(parts)


def list_wiki_articles() -> list[Path]:
    """List all wiki article files."""
    articles = []
    for subdir in [_config.CONCEPTS_DIR, _config.CONNECTIONS_DIR, _config.QA_DIR]:
        if subdir.exists():
            articles.extend(sorted(subdir.glob("*.md")))
    return articles


def list_raw_files() -> list[Path]:
    """List all daily log files."""
    if not _config.DAILY_DIR.exists():
        return []
    return sorted(_config.DAILY_DIR.glob("*.md"))


# ── Index helpers ─────────────────────────────────────────────────────


def count_inbound_links(target: str, exclude_file: Path | None = None) -> int:
    """Count how many wiki articles link to a given target."""
    count = 0
    target_escaped = re.escape(target)
    pattern = re.compile(rf"\[\[{target_escaped}(?:\||\]\])")
    for article in list_wiki_articles():
        if article == exclude_file:
            continue
        content = article.read_text(encoding="utf-8")
        if pattern.search(content):
            count += 1
    return count


def get_knowledge_dir() -> Path:
    """Get the knowledge directory path (for monkeypatching in tests)."""
    return _config.KNOWLEDGE_DIR


def get_article_word_count(path: Path) -> int:
    """Count words in an article, excluding YAML frontmatter."""
    content = path.read_text(encoding="utf-8")
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3 :]
    return len(content.split())


def build_index_entry(rel_path: str, summary: str, sources: str, updated: str) -> str:
    """Build a single index table row."""
    link = rel_path.replace(".md", "")
    return f"| [[{link}]] | {summary} | {sources} | {updated} |"


# ── TF-IDF helpers (shared between query.py and index.py) ─────────────


def _tokenize(text: str) -> list[str]:
    """Simple tokenization: lowercase words, ignore short tokens."""
    return [w for w in re.findall(r"[a-z]{2,}", text.lower()) if len(w) > 2]


def _compute_tf_idf(
    documents: list[tuple[str, str]],
) -> tuple[dict[str, dict[str, float]], dict[str, float]]:
    """Compute TF-IDF scores for a corpus.

    Returns (document_vectors, idf_scores).
    """
    tfs: list[Counter[str]] = []
    doc_names: list[str] = []
    for name, content in documents:
        tokens = _tokenize(content)
        tfs.append(Counter(tokens))
        doc_names.append(name)

    df: Counter[str] = Counter()
    for tf in tfs:
        for term in tf:
            df[term] += 1

    N = len(documents)
    idf = {term: math.log((N + 1) / (df[term] + 1)) + 1 for term in df}

    vectors: dict[str, dict[str, float]] = {}
    for name, tf in zip(doc_names, tfs):
        vectors[name] = {
            term: (count / max(tf.values())) * idf[term] for term, count in tf.items()
        }

    return vectors, idf
