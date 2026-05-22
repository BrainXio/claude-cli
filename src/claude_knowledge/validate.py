"""Validate knowledge base structural health.

Runs 6 structural checks: broken links, orphan pages, orphan sources,
stale articles, missing backlinks, and sparse articles.
"""

from __future__ import annotations

import argparse
from typing import Any

from claude_knowledge._config import KNOWLEDGE_DIR, REPORTS_DIR, now_iso, today_iso
from claude_knowledge._utils import (
    count_inbound_links,
    extract_wikilinks,
    file_hash,
    get_article_word_count,
    list_raw_files,
    list_wiki_articles,
    load_state,
    save_state,
    wiki_article_exists,
)


def check_broken_links() -> list[dict[str, Any]]:
    """Check for [[wikilinks]] that point to non-existent articles."""
    issues: list[dict[str, Any]] = []
    for article in list_wiki_articles():
        content = article.read_text(encoding="utf-8")
        rel = article.relative_to(KNOWLEDGE_DIR)
        for link in extract_wikilinks(content):
            if link.startswith("daily/"):
                continue
            if not wiki_article_exists(link):
                issues.append(
                    {
                        "severity": "error",
                        "check": "broken_link",
                        "file": str(rel),
                        "detail": f"Broken link: [[{link}]] - target does not exist",
                    }
                )
    return issues


def check_orphan_pages() -> list[dict[str, Any]]:
    """Check for articles with zero inbound links."""
    issues: list[dict[str, Any]] = []
    for article in list_wiki_articles():
        rel = article.relative_to(KNOWLEDGE_DIR)
        link_target = str(rel).replace(".md", "").replace("\\", "/")
        inbound = count_inbound_links(link_target)
        if inbound == 0:
            issues.append(
                {
                    "severity": "warning",
                    "check": "orphan_page",
                    "file": str(rel),
                    "detail": f"Orphan page: no other articles link to [[{link_target}]]",
                }
            )
    return issues


def check_orphan_sources() -> list[dict[str, Any]]:
    """Check for daily logs that haven't been compiled yet."""
    state = load_state()
    ingested = state.get("ingested", {})
    issues = []
    for log_path in list_raw_files():
        if log_path.name not in ingested:
            issues.append(
                {
                    "severity": "warning",
                    "check": "orphan_source",
                    "file": f"daily/{log_path.name}",
                    "detail": f"Uncompiled daily log: {log_path.name} has not been ingested",
                }
            )
    return issues


def check_stale_articles() -> list[dict[str, Any]]:
    """Check if source daily logs have changed since compilation."""
    state = load_state()
    ingested = state.get("ingested", {})
    issues = []
    for log_path in list_raw_files():
        rel = log_path.name
        if rel in ingested:
            stored_hash = ingested[rel].get("hash", "")
            current_hash = file_hash(log_path)
            if stored_hash != current_hash:
                issues.append(
                    {
                        "severity": "warning",
                        "check": "stale_article",
                        "file": f"daily/{rel}",
                        "detail": f"Stale: {rel} has changed since last compilation",
                    }
                )
    return issues


def check_missing_backlinks() -> list[dict[str, Any]]:
    """Check for asymmetric links between concept articles."""
    issues = []
    for article in list_wiki_articles():
        content = article.read_text(encoding="utf-8")
        rel = article.relative_to(KNOWLEDGE_DIR)
        source_link = str(rel).replace(".md", "").replace("\\", "/")

        if not source_link.startswith("concepts/"):
            continue

        for link in extract_wikilinks(content):
            if link.startswith("daily/"):
                continue
            target_path = KNOWLEDGE_DIR / f"{link}.md"
            if not target_path.exists():
                continue
            if not link.startswith("concepts/"):
                continue
            target_content = target_path.read_text(encoding="utf-8")
            if f"[[{source_link}]]" not in target_content:
                issues.append(
                    {
                        "severity": "suggestion",
                        "check": "missing_backlink",
                        "file": str(rel),
                        "detail": f"[[{source_link}]] links to [[{link}]] but not vice versa",
                        "auto_fixable": True,
                    }
                )
    return issues


def check_sparse_articles() -> list[dict[str, Any]]:
    """Check for articles with fewer than 200 words."""
    issues = []
    for article in list_wiki_articles():
        word_count = get_article_word_count(article)
        if word_count < 200:
            rel = article.relative_to(KNOWLEDGE_DIR)
            issues.append(
                {
                    "severity": "suggestion",
                    "check": "sparse_article",
                    "file": str(rel),
                    "detail": f"Sparse article: {word_count} words (minimum recommended: 200)",
                }
            )
    return issues


def generate_report(all_issues: list[dict[str, Any]]) -> str:
    """Generate a markdown lint report."""
    errors = [i for i in all_issues if i["severity"] == "error"]
    warnings = [i for i in all_issues if i["severity"] == "warning"]
    suggestions = [i for i in all_issues if i["severity"] == "suggestion"]

    lines = [
        f"# Lint Report - {today_iso()}",
        "",
        f"**Total issues:** {len(all_issues)}",
        f"- Errors: {len(errors)}",
        f"- Warnings: {len(warnings)}",
        f"- Suggestions: {len(suggestions)}",
        "",
    ]

    for severity, issues, marker in [
        ("Errors", errors, "x"),
        ("Warnings", warnings, "!"),
        ("Suggestions", suggestions, "?"),
    ]:
        if issues:
            lines.append(f"## {severity}")
            lines.append("")
            for issue in issues:
                fixable = " (auto-fixable)" if issue.get("auto_fixable") else ""
                lines.append(
                    f"- **[{marker}]** `{issue['file']}` - {issue['detail']}{fixable}"
                )
            lines.append("")

    if not all_issues:
        lines.append("All checks passed. Knowledge base is healthy.")
        lines.append("")

    return "\n".join(lines)


def validate_kb() -> dict[str, Any]:
    """Run all structural checks and return a summary dict."""
    checks = [
        ("Broken links", check_broken_links),
        ("Orphan pages", check_orphan_pages),
        ("Orphan sources", check_orphan_sources),
        ("Stale articles", check_stale_articles),
        ("Missing backlinks", check_missing_backlinks),
        ("Sparse articles", check_sparse_articles),
    ]

    all_issues: list[dict[str, Any]] = []
    for name, check_fn in checks:
        issues = check_fn()
        all_issues.extend(issues)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = generate_report(all_issues)
    report_path = REPORTS_DIR / f"lint-{today_iso()}.md"
    report_path.write_text(report, encoding="utf-8")

    state = load_state()
    state["last_lint"] = now_iso()
    save_state(state)

    return {
        "issues": {
            "errors": sum(1 for i in all_issues if i["severity"] == "error"),
            "warnings": sum(1 for i in all_issues if i["severity"] == "warning"),
            "suggestions": sum(1 for i in all_issues if i["severity"] == "suggestion"),
        },
        "report_path": str(report_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the knowledge base")
    parser.parse_args()

    print("Running knowledge base validation...")
    result = validate_kb()
    issues = result["issues"]
    print(
        f"Results: {issues['errors']} errors, {issues['warnings']} warnings, {issues['suggestions']} suggestions"
    )
    print(f"Report: {result['report_path']}")

    return 1 if issues["errors"] > 0 else 0


if __name__ == "__main__":
    exit(main())
