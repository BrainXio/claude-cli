"""Knowledge engine pipeline coordinator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from claude_knowledge import ingest, compile, validate, scan


def run_pipeline(
    source: str | Path = ".",
    *,
    dry_run: bool = False,
    force_all: bool = False,
) -> dict[str, Any]:
    """Run the full knowledge pipeline: scan, ingest, compile, validate.

    Args:
        source: Directory to scan and ingest from.
        dry_run: Report what would change without writing.
        force_all: Re-ingest all files regardless of change detection.

    Returns:
        Summary dict with counts and any errors.
    """
    results: dict[str, Any] = {}
    src = Path(source).resolve()

    # 1. Scan for prototype projects
    prototypes = scan.scan_prototypes(src)
    results["prototypes_found"] = len(prototypes)

    # 2. Ingest raw markdown
    ingest_report = ingest.ingest_dir(src, dry_run=dry_run, force_all=force_all)
    results["ingested"] = ingest_report.get("ingested", 0)
    results["unchanged"] = ingest_report.get("unchanged", 0)
    results["errors"] = ingest_report.get("errors", [])

    # 3. Compile daily logs to articles
    compile_report = compile.compile_logs(dry_run=dry_run)
    results["compiled"] = compile_report.get("compiled", 0)

    # 4. Validate KB health
    validation = validate.validate_kb()
    results["issues"] = validation.get("issues", {})

    return results
