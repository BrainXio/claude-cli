"""Tests for claude_cli._llm."""

import sys
from typing import Any


sys.path.insert(0, "/home/mister-robot/workspace/claude-cli/src")


def test_provider_is_runtime_checkable():
    """Provider protocol can be checked at runtime."""
    from claude_cli._llm import Provider

    assert hasattr(Provider, "__protocol_attrs__")


def test_fake_provider_satisfies_protocol():
    """A minimal fake class satisfies the Provider protocol."""
    from claude_cli._llm import Provider

    class Fake:
        def list_models(self) -> list[dict[str, Any]]:
            return []

        def show_model(self, model_name: str) -> tuple[str, bool]:
            return "", False

    assert isinstance(Fake(), Provider)


def test_incomplete_provider_fails_protocol():
    """A class missing a method does not satisfy Provider."""
    from claude_cli._llm import Provider

    class Bad:
        def list_models(self) -> list[dict[str, Any]]:
            return []

    assert not isinstance(Bad(), Provider)
