# ADR-002: Pre-Commit pytest --co Smoke Test

## Status

Accepted

## Context

The pre-commit quality gate (`claude-pre-commit`) ran ruff, mdformat, and mypy but did not run any pytest validation. This meant import errors and test collection failures were not caught before commit.

## Decision

Add `pytest --co -q` (collect-only) to the pre-commit hook with a 10-second timeout. If the test collection consistently exceeds 6 seconds in practice, make it optional via `CLAUDE_STRICT_PRECOMMIT=1`.

The goal is catching import errors and collection failures without killing developer velocity.

## Consequences

- **Positive**: Import errors and broken test files are caught before commit
- **Positive**: Fast (\<2s) because it does not run tests, only collects them
- **Negative**: Adds ~1s to pre-commit time
