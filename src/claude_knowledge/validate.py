"""Validate knowledge base structural health.

Runs 6 structural checks: broken links, orphan pages, orphan sources,
stale articles, missing backlinks, and sparse articles.
"""

from __future__ import annotations

import argparse
from typing import Any

from claude_knowledge import _utils
from claude_knowledge._config import get_reports_dir, now_iso, today_iso


def check_broken_links() -> list[dict[str, Any]]:
    """Check for [[wikilinks]] that point to non-existent articles."""
    issues: list[dict[str, Any]] = []
    knowledge_dir = _utils.get_knowledge_dir()
    for article in _utils.list_wiki_articles():
        content = article.read_text(encoding="utf-8")
        rel = article.relative_to(knowledge_dir)
        for link in _utils.extract_wikilinks(content):
            if link.startswith("daily/"):
                continue
            if not _utils.wiki_article_exists(link):
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
    knowledge_dir = _utils.get_knowledge_dir()
    for article in _utils.list_wiki_articles():
        rel = article.relative_to(knowledge_dir)
        link_target = str(rel).replace(".md", "").replace("\\", "/")
        inbound = _utils.count_inbound_links(link_target)
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
    state = _utils.load_state()
    ingested = state.get("ingested", {})
    issues = []
    for log_path in _utils.list_raw_files():
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
    state = _utils.load_state()
    ingested = state.get("ingested", {})
    issues = []
    for log_path in _utils.list_raw_files():
        rel = log_path.name
        if rel in ingested:
            stored_hash = ingested[rel].get("hash", "")
            current_hash = _utils.file_hash(log_path)
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
    knowledge_dir = _utils.get_knowledge_dir()
    for article in _utils.list_wiki_articles():
        content = article.read_text(encoding="utf-8")
        rel = article.relative_to(knowledge_dir)
        source_link = str(rel).replace(".md", "").replace("\\", "/")

        if not source_link.startswith("concepts/"):
            continue

        for link in _utils.extract_wikilinks(content):
            if link.startswith("daily/"):
                continue
            target_path = knowledge_dir / f"{link}.md"
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
    knowledge_dir = _utils.get_knowledge_dir()
    for article in _utils.list_wiki_articles():
        word_count = _utils.get_article_word_count(article)
        if word_count < 200:
            rel = article.relative_to(knowledge_dir)
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

    reports_dir = get_reports_dir()
    reports_dir.mkdir(parents=True, exist_ok=True)
    report = generate_report(all_issues)
    report_path = reports_dir / f"lint-{today_iso()}.md"
    report_path.write_text(report, encoding="utf-8")

    state = _utils.load_state()
    state["last_lint"] = now_iso()
    _utils.save_state(state)

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
