"""Tests for claude_cli.standards_guard."""

import io
import json
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, "/home/mister-robot/workspace/claude-cli/src")


def _stdin(data: dict) -> io.StringIO:
    return io.StringIO(json.dumps(data))


def test_is_guarded_path():
    from claude_cli.standards_guard import is_guarded_path

    assert is_guarded_path(".github/README.md") is True
    assert is_guarded_path("project/README.md") is True
    assert is_guarded_path("CONTRIBUTING.md") is True
    assert is_guarded_path("SECURITY.md") is True
    assert is_guarded_path("src/claude_cli/__init__.py") is False
    assert is_guarded_path("README") is False
    assert is_guarded_path("docs/GUIDE.md") is False


def test_is_workflow_file():
    from claude_cli.standards_guard import is_workflow_file

    assert is_workflow_file(".github/workflows/build.yml") is True
    assert is_workflow_file(".github/workflows/test.yaml") is True
    assert is_workflow_file(".github/workflows/release.yml") is True
    assert is_workflow_file("src/workflows/build.yml") is False
    assert is_workflow_file("build.yml") is False
    assert is_workflow_file("README.md") is False


def test_check_content_no_violations():
    from claude_cli.standards_guard import check_content

    violations = check_content(
        "This is normal documentation.\nNo forbidden patterns.", "README.md"
    )
    assert violations == []


def test_check_content_philosophy_sludge():
    from claude_cli.standards_guard import check_content

    violations = check_content(
        "This project is local-first.\nNo, really, it is quiet joy all the way.",
        "README.md",
    )
    assert len(violations) == 2
    assert "local-first" in violations[0]
    assert "quiet joy" in violations[1]


def test_check_content_manifesto_tone():
    from claude_cli.standards_guard import check_content

    violations = check_content(
        "This must be managed exclusively through the admin API.", "README.md"
    )
    assert len(violations) == 1
    assert "managed exclusively through" in violations[0]


def test_check_content_phantom_repo():
    from claude_cli.standards_guard import check_content

    content = (
        "See https://github.com/brainxio/tools for more info.\n"
        "And https://github.com/evil/hack for bad stuff."
    )
    violations = check_content(content, "README.md")
    assert len(violations) == 1
    assert "evil/hack" in violations[0]


def test_check_workflow_content_no_violations():
    from claude_cli.standards_guard import check_workflow_content

    content = """jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
"""
    violations = check_workflow_content(content, ".github/workflows/build.yml")
    assert violations == []


def test_check_workflow_content_floating_tags():
    from claude_cli.standards_guard import check_workflow_content

    content = "https://github.com/actions/checkout@latest"
    violations = check_workflow_content(content, ".github/workflows/build.yml")
    assert len(violations) == 1
    assert "floating tag" in violations[0]


def test_check_workflow_content_curl_sudo():
    from claude_cli.standards_guard import check_workflow_content

    content = "curl | sudo bash"
    violations = check_workflow_content(content, ".github/workflows/build.yml")
    assert len(violations) == 1
    assert "curl|sudo/bash" in violations[0]


def test_main_valid_json_no_file_path(capsys: pytest.CaptureFixture) -> None:
    from claude_cli.standards_guard import main

    with patch.object(
        sys,
        "stdin",
        _stdin(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "", "new_string": "content"},
            }
        ),
    ):
        main()
    captured = capsys.readouterr()
    assert captured.out == ""


def test_main_valid_json_allowed_repo(capsys: pytest.CaptureFixture) -> None:
    from claude_cli.standards_guard import main

    with patch.object(
        sys,
        "stdin",
        _stdin(
            {
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": ".github/README.md",
                    "new_string": "https://github.com/brainxio/tools is allowed",
                },
            }
        ),
    ):
        main()
    captured = capsys.readouterr()
    assert captured.out == ""


def test_main_valid_json_workflow(capsys: pytest.CaptureFixture) -> None:
    from claude_cli.standards_guard import main

    with patch.object(
        sys,
        "stdin",
        _stdin(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": ".github/workflows/test.yml",
                    "content": "jobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4",
                },
            }
        ),
    ):
        main()
    captured = capsys.readouterr()
    assert captured.out == ""


def test_main_invalid_json(capsys: pytest.CaptureFixture) -> None:
    from claude_cli.standards_guard import main

    with patch.object(sys, "stdin", io.StringIO("not valid json")):
        main()
    captured = capsys.readouterr()
    assert captured.out == ""


def test_main_eof_error(capsys: pytest.CaptureFixture) -> None:
    from claude_cli.standards_guard import main

    class _EOF(io.StringIO):
        def read(self, *args, **kwargs):
            raise EOFError

    with patch.object(sys, "stdin", _EOF()):
        main()
    captured = capsys.readouterr()
    assert captured.out == ""


def test_main_edit_tool(capsys: pytest.CaptureFixture) -> None:
    from claude_cli.standards_guard import main

    with patch.object(
        sys,
        "stdin",
        _stdin(
            {
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": ".github/README.md",
                    "new_string": "local-first is forbidden",
                },
            }
        ),
    ):
        main()
    captured = capsys.readouterr()
    assert "deny" in captured.out
    assert "philosophy sludge" in captured.out


def test_main_write_tool(capsys: pytest.CaptureFixture) -> None:
    from claude_cli.standards_guard import main

    with patch.object(
        sys,
        "stdin",
        _stdin(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "CONTRIBUTING.md",
                    "content": "sacred is forbidden",
                },
            }
        ),
    ):
        main()
    captured = capsys.readouterr()
    assert "deny" in captured.out
    assert "philosophy sludge" in captured.out


def test_main_unsupported_tool(capsys: pytest.CaptureFixture) -> None:
    from claude_cli.standards_guard import main

    with patch.object(
        sys,
        "stdin",
        _stdin({"tool_name": "Read", "tool_input": {"file_path": "README.md"}}),
    ):
        main()
    captured = capsys.readouterr()
    assert captured.out == ""


def test_main_no_content(capsys: pytest.CaptureFixture) -> None:
    from claude_cli.standards_guard import main

    with patch.object(
        sys,
        "stdin",
        _stdin(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "README.md", "new_string": ""},
            }
        ),
    ):
        main()
    captured = capsys.readouterr()
    assert captured.out == ""


def test_main_violation_count_truncation(capsys: pytest.CaptureFixture) -> None:
    from claude_cli.standards_guard import main

    with patch.object(
        sys,
        "stdin",
        _stdin(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": ".github/README.md",
                    "content": "local-first\nquiet joy\nsacred\nCore approval\nAnother Intelligence\nsovereign AI",
                },
            }
        ),
    ):
        main()
    captured = capsys.readouterr()
    assert "and 1 more" in captured.out


def test_check_content_case_insensitive():
    from claude_cli.standards_guard import check_content

    violations = check_content("LOCAL-FIRST is the way", "README.md")
    assert len(violations) == 1


def test_check_content_with_special_characters():
    from claude_cli.standards_guard import check_content

    content = "https://github.com/evil/hack with special chars: emojis"
    violations = check_content(content, "README.md")
    assert len(violations) == 1
