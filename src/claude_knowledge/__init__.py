"""Claude knowledge package — per-repo knowledge engine."""

from claude_knowledge.engine import run_pipeline
from claude_knowledge.ingest import ingest_dir
from claude_knowledge.compile import compile_logs
from claude_knowledge.query import query_kb
from claude_knowledge.validate import validate_kb

__all__ = [
    "run_pipeline",
    "ingest_dir",
    "compile_logs",
    "query_kb",
    "validate_kb",
]
