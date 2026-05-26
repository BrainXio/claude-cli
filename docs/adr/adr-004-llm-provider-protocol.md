# ADR-004: Minimal LLM Provider Protocol

## Status

Accepted

## Context

`check_model_vision.py` hardcoded Ollama and Anthropic env vars. The model interaction was not swappable, making future provider changes expensive.

## Decision

Introduce `claude_cli._llm.Provider` as a `@runtime_checkable` Protocol with exactly two methods:

- `list_models() -> list[dict[str, Any]]`
- `show_model(model_name: str) -> tuple[str, bool]`

Implement only `OllamaProvider`. No YAGNI — the protocol exists but is not grown beyond today's needs.

## Consequences

- **Positive**: `check_model_vision()` can be tested with mock providers
- **Positive**: Future provider addition requires only a new class, no protocol changes
- **Negative**: The protocol is intentionally minimal; richer interaction patterns may need extension later
