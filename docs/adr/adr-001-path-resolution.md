# ADR-001: Path Resolution via Environment Variable + importlib.resources

## Status

Accepted

## Context

`dispatch.py` originally resolved the `claude-workflows` directory using a brittle `Path(__file__)` chain:

```python
WORKFLOW_DIR = Path(__file__).resolve().parent.parent.parent / "claude-workflows"
```

This breaks when the package is installed via `uvx` or `pipx` because the source files are not in a predictable filesystem location relative to the workflows.

## Decision

Resolve `WORKFLOW_DIR` via a `CLAUDE_WORKFLOWS_DIR` environment variable, with a fallback to `importlib.resources` exclusively. The `pkg_resources` module is deprecated and must not be used.

## Consequences

- **Positive**: Works under `uvx`, `pipx`, editable installs, and production deployments
- **Positive**: No dependency on `pkg_resources`
- **Negative**: Requires users to set `CLAUDE_WORKFLOWS_DIR` when workflows are outside the package
