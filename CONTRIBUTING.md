# Contributing to claude-cli

Thank you for contributing to the BrainXio Claude Code extension framework.

For organization-wide conventions (branch naming, conventional commits, pull request checklist, signed commits), see [BrainXio/.github/CONTRIBUTING.md](https://github.com/BrainXio/.github/blob/main/CONTRIBUTING.md). This document covers Python-specific development for the `claude-cli` package.

## Development Setup

### Prerequisites

| Tool   | Version    | Purpose                |
| ------ | ---------- | ---------------------- |
| `git`  | any recent | Version control        |
| Python | 3.10+      | Runtime                |
| `uv`   | latest     | Python package manager |

### Clone

```bash
git clone https://github.com/BrainXio/claude-cli.git
cd claude-cli
```

### Install

```bash
uv sync
```

This installs the package in editable mode with all dev dependencies.

## Local Commands

### Run Tests

```bash
uv run pytest
```

With coverage report:

```bash
uv run pytest --cov=src/claude_cli --cov-report=term-missing --cov-fail-under=90
```

### Lint

```bash
uv run ruff check .
```

Auto-fix issues:

```bash
uv run ruff check . --fix
```

### Format

```bash
uv run ruff format .
```

### Type Check

```bash
uv run mypy src/ --strict
```

### Markdown Format Check

```bash
uvx --with mdformat-frontmatter --with mdformat-gfm mdformat --check .
```

## Architecture Overview

The `claude-cli` package is organized into three namespaces:

### `claude_cli`

Core CLI hooks and utilities that integrate with Claude Code's lifecycle:

- **bootstrap** — Session bootstrap that initializes bus state, knowledge engine, and identity tracking.
- **session-start** / **session-end** — Hooks called at session boundaries for setup and teardown.
- **pre-compact** — Pre-compaction hook for context preservation before session compaction.
- **pre-commit** — Quality gate that runs ruff, mypy, and pytest before allowing commits.
- **standards-guard** — PreToolUse hook that blocks forbidden content in standards docs and workflow files.
- **check-model-vision** — Detects vision capability for configured Ollama models.
- **dispatch** — Workflow dispatch engine for multi-stage agent pipelines.
- **statusline** — Generates session statusline output.

### `claude_knowledge`

Knowledge base pipeline for ingesting, compiling, and querying markdown content:

- **ingest** — Converts raw markdown files into tracked JSON artifacts.
- **compile** — Aggregates daily logs into structured knowledge articles.
- **query** — Semantic search over the knowledge base using TF-IDF.
- **validate** — Structural consistency checks (broken links, orphans, stale articles).
- **engine** — Orchestrates the full ingest-compile-validate pipeline.

### `claude_quality`

Quality gates and mode management for enforcing code standards:

- **modes** — Operational mode system (developer, research, review, ops, personal).
- **gate** — Quality gate evaluation with configurable thresholds.
- **schemas** — Validation schemas for structured data.
- **precedents** — Precedent tracking for quality decisions.
- **anti-gaming** — Metrics to detect and prevent gaming of quality systems.

## Commit Conventions

This repository follows [Conventional Commits](https://www.conventionalcommits.org/). See the org-wide [CONTRIBUTING.md](https://github.com/BrainXio/.github/blob/main/CONTRIBUTING.md) for the full specification.

Common types for this repo:

- `feat` — New hook or CLI command
- `fix` — Bug fix in hook logic
- `refactor` — Internal restructuring with no behavior change
- `test` — Adding or updating tests
- `docs` — Documentation-only changes
- `chore` — Dependency updates, CI config changes

## Version Pinning Policy

All GitHub Actions `uses:` references must follow the BrainXio version pinning policy documented in the org-wide [CONTRIBUTING.md](https://github.com/BrainXio/.github/blob/main/CONTRIBUTING.md).

Summary:

- Third-party actions → full commit SHA with trailing version comment
- Internal actions (`BrainXio/*`) → semver tag (e.g., `@v1`)

## Testing Individual Hooks

Hooks are registered as console scripts in `pyproject.toml`. During development you can run them directly:

```bash
# Quality gate (dry-run)
uv run claude-pre-commit

# Standards guard (pipe JSON via stdin)
echo '{"tool":"Edit","path":"src/claude_cli/foo.py"}' | uv run claude-standards-guard

# Model vision check
uv run claude-check-model-vision

# Workflow dispatch (dry-run)
uv run claude-dispatch my-workflow --dry-run
```

## Related Projects

- [BrainXio/claude-config](https://github.com/BrainXio/claude-config) — Framework configuration for `.claude/` settings, agents, rules, skills, and workflows.
- [BrainXio/.github](https://github.com/BrainXio/.github) — Organization-level GitHub templates, CI workflows, and contribution guidelines.
