# CLAUDE.md

BrainXio claude-cli Python package — lifecycle hooks, quality gates, and CLI utilities for Claude Code.

## Entry Points (`pyproject.toml` `[project.scripts]`)

| Command                     | Module                               | Purpose                                      |
| --------------------------- | ------------------------------------ | -------------------------------------------- |
| `claude-bootstrap`          | `claude_cli.bootstrap:main`          | Session bootstrap (bus, KB engine, identity) |
| `claude-session-start`      | `claude_cli.session_start:main`      | Session start hook (model capability detect) |
| `claude-session-end`        | `claude_cli.session_end:main`        | Session end hook (cleanup, summary)          |
| `claude-pre-compact`        | `claude_cli.pre_compact:main`        | Pre-compaction context preservation          |
| `claude-pre-commit`         | `claude_cli.pre_commit:main`         | Quality gate (ruff, mypy, pytest)            |
| `claude-standards-guard`    | `claude_cli.standards_guard:main`    | PreToolUse validator for Edit/Write          |
| `claude-post-tool-use`      | `claude_cli.post_tool_use:main`      | PostToolUse hook — error detection & incident response |
| `claude-check-model-vision` | `claude_cli.check_model_vision:main` | Vision capability detection                  |
| `claude-dispatch`           | `claude_cli.dispatch:main`           | Workflow dispatch engine                     |
| `claude-knowledge`          | `claude_knowledge.cli:main`          | KB pipeline CLI (ingest, compile, query)     |
| `claude-statusline`         | `claude_cli.statusline:main`         | Statusline generator                         |
| `claude-commit`             | `claude_cli.commit:main`             | Automated commits with rule enforcement      |
| `claude-bus`                | `claude_cli._bus:main`               | Inter-session bus CLI (read, write, claim)   |

## Development

```bash
cd packages/brainxio-claude-cli
uv run pytest                    # 100+ tests
uv run ruff check .              # Lint
uv run mypy src/claude_cli/ --strict  # Type check
uv run mdformat --check .        # Markdown (with plugins)
```

## Key Modules

- `bootstrap.py` — Session initialization
- `pre_commit.py` — Quality gate with auto-fix retry
- `standards_guard.py` — Edit/Write validation against rules
- `commit.py` — Secret scanning, conventional commits, no-attribution enforcement
