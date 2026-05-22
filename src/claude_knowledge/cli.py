"""CLI entry point for knowledge base operations."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from claude_knowledge import compile, ingest, query, validate


def _cmd_ingest(args: argparse.Namespace) -> int:
    report = ingest.ingest_dir(
        args.source, dry_run=args.dry_run, force_all=args.force_all
    )
    print(json.dumps(report, indent=2))
    return 0 if not report.get("errors") else 1


def _cmd_compile(args: argparse.Namespace) -> int:
    report = compile.compile_logs(dry_run=args.dry_run)
    print(json.dumps(report, indent=2))
    return 0 if not report.get("errors") else 1


def _cmd_query(args: argparse.Namespace) -> int:
    results: list[dict[str, Any]] = query.query_kb(
        args.question,
        top_k=args.top_k,
        min_version=args.min_version,
        max_version=args.max_version,
    )
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for i, r in enumerate(results, 1):
            print(f"{i}. [{r['score']}] {r['source']}")
            print(f"   {r['excerpt'][:200]}")
            print()
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    report = validate.validate_kb()
    print(json.dumps(report, indent=2))
    issues = report.get("issues", {})
    return (
        0
        if issues.get("errors", 0) == 0
        and issues.get("warnings", 0) == 0
        and issues.get("suggestions", 0) == 0
        else 1
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="claude-knowledge", description="Knowledge base operations"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ingest
    p_ingest = sub.add_parser("ingest", help="Ingest markdown files into the KB")
    p_ingest.add_argument("source", nargs="?", default=".", help="Directory to scan")
    p_ingest.add_argument("--dry-run", action="store_true")
    p_ingest.add_argument("--force-all", action="store_true")
    p_ingest.set_defaults(func=_cmd_ingest)

    # compile
    p_compile = sub.add_parser("compile", help="Compile daily logs into articles")
    p_compile.add_argument("--dry-run", action="store_true")
    p_compile.set_defaults(func=_cmd_compile)

    # query
    p_query = sub.add_parser("query", help="Query the KB via TF-IDF search")
    p_query.add_argument("question", help="Natural language query")
    p_query.add_argument("--top-k", type=int, default=5)
    p_query.add_argument("--min-version", type=int, default=None)
    p_query.add_argument("--max-version", type=int, default=None)
    p_query.add_argument("--json", action="store_true", help="Output raw JSON")
    p_query.set_defaults(func=_cmd_query)

    # validate
    p_validate = sub.add_parser("validate", help="Validate KB health")
    p_validate.set_defaults(func=_cmd_validate)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
