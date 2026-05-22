"""Article type templates for KB scaffolding."""

from __future__ import annotations

from typing import Any


_ARTICLE_TEMPLATES: dict[str, dict[str, Any]] = {
    "concept": {
        "required_frontmatter": ["title", "type"],
        "optional_frontmatter": ["aliases", "tags", "sources"],
        "body_sections": [
            "## Definition",
            "## Key Properties",
            "## Related Concepts",
        ],
    },
    "mechanism": {
        "required_frontmatter": ["title", "type"],
        "optional_frontmatter": ["aliases", "tags", "sources"],
        "body_sections": [
            "## How It Works",
            "## Inputs & Outputs",
            "## Edge Cases",
        ],
    },
    "outcome": {
        "required_frontmatter": ["title", "type"],
        "optional_frontmatter": ["aliases", "tags", "sources"],
        "body_sections": [
            "## Result",
            "## Context",
            "## Impact",
        ],
    },
    "reference": {
        "required_frontmatter": ["title", "type"],
        "optional_frontmatter": ["aliases", "tags", "sources"],
        "body_sections": [
            "## Summary",
            "## Details",
            "## See Also",
        ],
    },
    "connection": {
        "required_frontmatter": ["title", "type"],
        "optional_frontmatter": ["aliases", "tags", "sources"],
        "body_sections": [
            "## From",
            "## To",
            "## Relationship",
        ],
    },
}


def get_template(article_type: str) -> dict[str, Any] | None:
    """Return the template for a given article type.

    Args:
        article_type: One of "concept", "mechanism", "outcome", "reference", "connection".

    Returns:
        Template dict with required_frontmatter, optional_frontmatter, body_sections.
        None if the type is unknown.
    """
    return _ARTICLE_TEMPLATES.get(article_type)


def list_types() -> list[str]:
    """Return all available article type names."""
    return list(_ARTICLE_TEMPLATES.keys())


def scaffold_article(
    article_type: str,
    title: str,
    **kwargs: Any,
) -> str:
    """Generate a scaffolded markdown article with proper frontmatter.

    Returns:
        Markdown string ready to be written to a file.
    """
    template = get_template(article_type)
    if template is None:
        raise ValueError(f"Unknown article type: {article_type}")

    lines: list[str] = ["---"]
    lines.append(f"title: {title}")
    lines.append(f"type: {article_type}")

    for key in template.get("optional_frontmatter", []):
        if key in kwargs:
            value = kwargs[key]
            if isinstance(value, list):
                value = json.dumps(value)
            lines.append(f"{key}: {value}")

    lines.append("---")
    lines.append("")

    for section in template.get("body_sections", []):
        lines.append(section)
        lines.append("")

    return "\n".join(lines)


import json  # noqa: E402 — imported late for scaffold_article
