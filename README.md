# claude-cli

Lifecycle hooks, quality gates, knowledge engine, and dispatch utilities for Claude Code sessions.

## Packages

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

## Install

```bash
uvx --from git+https://github.com/BrainXio/claude-cli claude-bootstrap
```

## Usage

### Bootstrap a session

```bash
claude-bootstrap
```

### Run the pre-commit quality gate

```bash
claude-pre-commit
```

### Ingest markdown files into the knowledge base

```bash
claude-knowledge ingest /path/to/source --dry-run
```

### Compile daily logs into articles

```bash
claude-knowledge compile --dry-run
```

### Query the knowledge base

```bash
claude-knowledge query "how does the dispatch engine work"
```

### Validate knowledge base health

```bash
claude-knowledge validate
```

### Dispatch a workflow

```bash
claude-dispatch my-workflow --dry-run
```

### Check model vision capability

```bash
claude-check-model-vision
```

## Commands

| Command                     | Purpose                                      |
| --------------------------- | -------------------------------------------- |
| `claude-bootstrap`          | Session bootstrap (bus, KB engine setup)     |
| `claude-session-start`      | Session start hook (model capability detect) |
| `claude-session-end`        | Session end hook (cleanup, summary)          |
| `claude-pre-compact`        | Pre-compaction hook (context preservation)   |
| `claude-pre-commit`         | Pre-commit hook (ruff, mypy, pytest)         |
| `claude-standards-guard`    | Standards enforcement before Edit/Write      |
| `claude-check-model-vision` | Detect Ollama vision capability              |
| `claude-dispatch`           | Workflow dispatch utility                    |
| `claude-knowledge`          | Knowledge engine CLI                         |
| `claude-statusline`         | Statusline generator                         |

## Development

```bash
uv run pytest              # Run tests
uv run ruff check .        # Lint
uv run ruff format .       # Format
uv run mypy src/ --strict  # Type check
```

Quality gates: ruff, mypy strict, pytest with 90% coverage threshold.

## Related Projects

- [BrainXio/claude-config](https://github.com/BrainXio/claude-config) — Framework configuration for `.claude/` settings, agents, rules, skills, and workflows. This package is designed to work alongside `claude-config` to provide the full Claude Code extension framework.
