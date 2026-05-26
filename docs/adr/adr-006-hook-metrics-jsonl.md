# ADR-006: Line-Oriented JSON Metrics (hook_metrics.jsonl)

## Status

Accepted

## Context

Phase 6 required minimal observability with zero external dependencies. The choice was between:

1. A structured log file (JSONL)
1. A metrics library (Prometheus, statsd)
1. A database (SQLite)

## Decision

Use append-only line-oriented JSON (`hook_metrics.jsonl`) with these properties:

- One JSON object per line
- Append-only (no locking needed for single-process hooks)
- Human-readable
- No schema enforcement (flexible)
- Zero external dependencies
- 10MB rotation threshold with 3 backups

The schema is intentionally minimal: `ts`, `hook`, `duration_ms`, `success`, `error_type`.

## Consequences

- **Positive**: Works without network, database, or metrics infrastructure
- **Positive**: Human-readable for debugging
- **Positive**: Can be streamed to Prometheus/statsd later if needed
- **Negative**: No built-in aggregation or querying — external tools required for analysis
- **Negative**: Rotation at 10MB provides ~12 years of retention at 100 hooks/day
