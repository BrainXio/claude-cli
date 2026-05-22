"""Tests for claude_cli._config."""

import sys
from unittest.mock import patch

sys.path.insert(0, "/home/mister-robot/workspace/claude-cli/src")


def test_get_allowed_repos_empty_default():
    """Test get_allowed_repos returns empty set when no env var."""
    from claude_cli._config import get_allowed_repos

    with patch.dict("os.environ", {}, clear=True):
        result = get_allowed_repos()
        assert result == set()


def test_get_allowed_repos_single_repo():
    """Test get_allowed_repos parses single repo from env var."""
    from claude_cli._config import get_allowed_repos

    with patch.dict("os.environ", {"CLAUDE_ALLOWED_REPOS": "BrainXio/claude-config"}):
        result = get_allowed_repos()
        assert result == {"BrainXio/claude-config"}


def test_get_allowed_repos_multiple_repos():
    """Test get_allowed_repos parses comma-separated repos."""
    from claude_cli._config import get_allowed_repos

    with patch.dict(
        "os.environ",
        {"CLAUDE_ALLOWED_REPOS": "BrainXio/claude-config, BrainXio/cicd,BrainXio/actions"},
    ):
        result = get_allowed_repos()
        assert result == {"BrainXio/claude-config", "BrainXio/cicd", "BrainXio/actions"}


def test_get_allowed_repos_whitespace_stripped():
    """Test get_allowed_repos strips whitespace from entries."""
    from claude_cli._config import get_allowed_repos

    with patch.dict(
        "os.environ",
        {"CLAUDE_ALLOWED_REPOS": "  BrainXio/claude-config  ,  BrainXio/cicd  "},
    ):
        result = get_allowed_repos()
        assert result == {"BrainXio/claude-config", "BrainXio/cicd"}


def test_get_allowed_repos_ignores_empty_entries():
    """Test get_allowed_repos ignores empty entries from trailing commas."""
    from claude_cli._config import get_allowed_repos

    with patch.dict("os.environ", {"CLAUDE_ALLOWED_REPOS": "BrainXio/claude-config,"}):
        result = get_allowed_repos()
        assert result == {"BrainXio/claude-config"}
