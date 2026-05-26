"""Minimal LLM provider protocol — zero dependencies."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Provider(Protocol):
    """Protocol for querying local LLM model capabilities.

    Implementations must be stateless or thread-safe. All methods
    should complete in <30s and never raise on network errors.
    """

    def list_models(self) -> list[dict[str, Any]]:
        """Return available models from the provider.

        Each dict must contain at least a ``name`` key.
        Returns an empty list on failure.
        """
        ...

    def show_model(self, model_name: str) -> tuple[str, bool]:
        """Return model metadata text and a success flag.

        The text format is provider-specific (e.g. Ollama's
        ``ollama show`` plain-text output).  Returns ``("", False)``
        on failure.
        """
        ...
