"""Prototype project scanning for ingestion shortlist."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def scan_prototypes(
    scan_dir: str | Path,
    *,
    output_file: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Scan a directory for prototype projects and return a shortlist.

    A prototype is detected by presence of typical project files:
    pyproject.toml, package.json, Cargo.toml, etc.
    """
    root = Path(scan_dir).resolve()
    sentinel_files = [
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "CMakeLists.txt",
        "setup.py",
        "requirements.txt",
    ]

    prototypes: list[dict[str, Any]] = []
    visited: set[Path] = set()

    for path in root.rglob("*"):
        if path.name in sentinel_files:
            project_dir = path.parent
            # Skip if this project is nested under another already-visited project
            if any(visited_dir in project_dir.parents for visited_dir in visited):
                continue
            if project_dir in visited:
                continue
            visited.add(project_dir)

            # Determine language/type
            lang = _detect_language(path.name)
            prototypes.append(
                {
                    "path": str(project_dir),
                    "name": project_dir.name,
                    "language": lang,
                    "sentinel": path.name,
                }
            )

    # Optionally write shortlist
    if output_file is not None:
        out = Path(output_file)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(prototypes, indent=2) + "\n")

    return prototypes


def _detect_language(sentinel: str) -> str:
    mapping = {
        "pyproject.toml": "python",
        "setup.py": "python",
        "requirements.txt": "python",
        "package.json": "javascript",
        "Cargo.toml": "rust",
        "go.mod": "go",
        "pom.xml": "java",
        "build.gradle": "java",
        "CMakeLists.txt": "cpp",
    }
    return mapping.get(sentinel, "unknown")
