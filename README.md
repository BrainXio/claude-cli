# BrainXio Claude CLI

Lifecycle hooks, quality gates, knowledge engine, and dispatch utilities for Claude Code sessions.

## Install

```bash
uvx --from git+https://github.com/BrainXio/claude-cli.git claude-bootstrap
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
| `claude-dispatch`           | Agent dispatch utility                       |
| `claude-knowledge`          | Knowledge engine CLI                         |
| `claude-statusline`         | Statusline generator                         |

## Development

```bash
cd /home/mister-robot/workspace/claude-cli
uv run pytest
```

Quality gates: ruff, mypy strict, pytest with coverage.

## Related Repositories

- BrainXio/claude-config
- BrainXio/claude-workflows
