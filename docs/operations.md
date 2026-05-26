# Operations Manual

For bus factor reduction: releases, secret rotation, and debugging the hook chain.

## Hook Chain Overview

The Claude Code extension framework runs these hooks in sequence during a session:

1. **SessionStart** (`claude-session-start`) — Detects model capabilities, injects KB context
1. **PreCompact** (`claude-pre-compact`) — Captures transcript before context compaction
1. **SessionEnd** (`claude-session-end`) — Extracts conversation context, spawns flush
1. **PreCommit** (`claude-pre-commit`) — Quality gate: ruff, mdformat, pytest smoke, mypy
1. **StandardsGuard** (`claude-standards-guard`) — PreToolUse hook blocking forbidden content
1. **Dispatch** (`claude-dispatch`) — Workflow dispatch engine

## Debugging Hook Failures

### Check hook_metrics.jsonl

```bash
tail -20 ~/.claude/data/hook_metrics.jsonl
```

Look for `success: false` entries. The `error_type` field shows the exception class.

### Check hook logs

Logs are written to `~/.claude/data/reports/logs/flush.log`:

```bash
tail -50 ~/.claude/data/reports/logs/flush.log
```

### Run a hook manually

```bash
# Standards guard (pipe JSON via stdin)
echo '{"tool_name":"Edit","tool_input":{"file_path":"src/foo.py","new_string":"x=1"}}' | uv run claude-standards-guard

# Pre-commit quality gate
uv run claude-pre-commit

# Check model vision
uv run claude-check-model-vision
```

### Common Failures

| Symptom                     | Cause                                        | Fix                                                                    |
| --------------------------- | -------------------------------------------- | ---------------------------------------------------------------------- |
| `pytest smoke: TIMEOUT`     | Large test suite or slow imports             | Run with `CLAUDE_STRICT_PRECOMMIT=1` to enforce, or skip if not strict |
| `Workflow not found`        | `CLAUDE_WORKFLOWS_DIR` not set or wrong path | `export CLAUDE_WORKFLOWS_DIR=/path/to/workflows`                       |
| `Context extraction failed` | Transcript file missing or corrupted         | Check `transcript_path` in stdin JSON                                  |

## Secret Rotation

### Gitleaks License

If `gitleaks detect` fails in CI with "license expired":

1. Generate new license at gitleaks.io
1. Update `GITLEAKS_LICENSE` secret in GitHub repository settings
1. Verify: push a test commit and check CI

### PyPI Token

If `publish.yml` fails with authentication error:

1. Generate new API token at pypi.org
1. Update `PYPI_API_TOKEN` secret in `claude-cli` repository settings
1. Re-run publish workflow

## Release Process

1. Update `CHANGELOG.md` with `[Unreleased]` changes
1. Tag release: `git tag v0.1.1 && git push origin v0.1.1`
1. CI publishes automatically via `publish.yml`
1. Verify on PyPI: `https://pypi.org/project/claude-cli/`

## Files That Matter in an Incident

| File                                    | What it tells you                                    |
| --------------------------------------- | ---------------------------------------------------- |
| `~/.claude/data/hook_metrics.jsonl`     | Which hooks failed and when                          |
| `~/.claude/data/reports/logs/flush.log` | SessionEnd and PreCompact execution details          |
| `~/.claude/data/state.json`             | Bootstrap state including agent_id, session_id, mode |
| `~/.claude/data/daily/*.md`             | Daily session logs (human-readable)                  |
