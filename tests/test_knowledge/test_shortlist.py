"""Tests for claude_knowledge.shortlist."""

import json
from pathlib import Path

import pytest

from claude_knowledge.shortlist import get_shortlist, update_shortlist


class TestGetShortlist:
    """Test get_shortlist function."""

    def test_empty_shortlist(self, tmp_path: Path) -> None:
        """Test getting shortlist when file doesn't exist."""
        result = get_shortlist(tmp_path / "nonexistent.json")
        assert result == []

    def test_empty_shortlist_from_kb_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test getting shortlist from KNOWLEDGE_DIR when file doesn't exist."""
        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)

        result = get_shortlist()
        assert result == []

    def test_load_existing_shortlist(self, tmp_path: Path) -> None:
        """Test loading an existing shortlist file."""
        shortlist_file = tmp_path / "shortlist.json"
        test_data = [
            {"path": "/path/to/project1", "name": "project1", "language": "python"},
            {"path": "/path/to/project2", "name": "project2", "language": "rust"},
        ]
        shortlist_file.write_text(json.dumps(test_data, indent=2))

        result = get_shortlist(shortlist_file)
        assert result == test_data

    def test_load_shortlist_with_prototypes_key(self, tmp_path: Path) -> None:
        """Test loading shortlist with 'prototypes' key."""
        shortlist_file = tmp_path / "shortlist.json"
        test_data = {
            "prototypes": [
                {"path": "/path/to/project1", "name": "project1", "language": "python"}
            ]
        }
        shortlist_file.write_text(json.dumps(test_data, indent=2))

        result = get_shortlist(shortlist_file)
        assert result == test_data["prototypes"]

    def test_load_empty_shortlist(self, tmp_path: Path) -> None:
        """Test loading an empty shortlist."""
        shortlist_file = tmp_path / "shortlist.json"
        shortlist_file.write_text("[]")

        result = get_shortlist(shortlist_file)
        assert result == []

    def test_load_invalid_json_returns_empty(self, tmp_path: Path) -> None:
        """Test that invalid JSON returns empty list."""
        shortlist_file = tmp_path / "shortlist.json"
        shortlist_file.write_text("not valid json")

        result = get_shortlist(shortlist_file)
        assert result == []

    def test_load_non_list_json_returns_empty(self, tmp_path: Path) -> None:
        """Test that non-list JSON returns empty list."""
        shortlist_file = tmp_path / "shortlist.json"
        shortlist_file.write_text('{"prototypes": "string"}')

        result = get_shortlist(shortlist_file)
        assert result == []


class TestUpdateShortlist:
    """Test update_shortlist function."""

    def test_create_new_shortlist(self, tmp_path: Path) -> None:
        """Test creating a new shortlist."""
        shortlist_file = tmp_path / "shortlist.json"
        test_prototypes = [
            {"path": "/path/to/project1", "name": "project1", "language": "python"},
        ]

        result_path = update_shortlist(test_prototypes, shortlist_file)

        assert result_path == shortlist_file
        assert shortlist_file.exists()
        content = json.loads(shortlist_file.read_text())
        assert content == test_prototypes

    def test_overwrite_existing_shortlist(self, tmp_path: Path) -> None:
        """Test overwriting an existing shortlist."""
        shortlist_file = tmp_path / "shortlist.json"
        old_prototypes = [
            {"path": "/path/to/old", "name": "old", "language": "unknown"},
        ]
        shortlist_file.write_text(json.dumps(old_prototypes, indent=2))

        new_prototypes = [
            {"path": "/path/to/new", "name": "new", "language": "python"},
        ]
        result_path = update_shortlist(new_prototypes, shortlist_file)

        assert result_path == shortlist_file
        content = json.loads(shortlist_file.read_text())
        assert content == new_prototypes

    def test_update_to_empty_list(self, tmp_path: Path) -> None:
        """Test updating to an empty list."""
        shortlist_file = tmp_path / "shortlist.json"
        old_prototypes = [
            {"path": "/path/to/project", "name": "project", "language": "python"},
        ]
        shortlist_file.write_text(json.dumps(old_prototypes, indent=2))

        result_path = update_shortlist([], shortlist_file)

        assert result_path == shortlist_file
        content = json.loads(shortlist_file.read_text())
        assert content == []

    def test_ensure_parent_directories(self, tmp_path: Path) -> None:
        """Test that parent directories are created."""
        shortlist_file = tmp_path / "nested" / "path" / "shortlist.json"
        test_prototypes = [
            {"path": "/path/to/project", "name": "project", "language": "python"},
        ]

        result_path = update_shortlist(test_prototypes, shortlist_file)

        assert result_path == shortlist_file
        assert shortlist_file.exists()
        assert shortlist_file.parent.exists()

    def test_default_to_kb_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that default path uses KNOWLEDGE_DIR."""
        mock_kb_dir = tmp_path / "knowledge"
        mock_kb_dir.mkdir()
        monkeypatch.setattr("claude_knowledge._config.KNOWLEDGE_DIR", mock_kb_dir)

        shortlist_file = mock_kb_dir / "shortlist.json"
        test_prototypes = [
            {"path": "/path/to/project", "name": "project", "language": "python"},
        ]

        result_path = update_shortlist(test_prototypes)

        assert result_path == shortlist_file
        assert shortlist_file.exists()
