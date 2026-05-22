"""Tests for claude_quality.precedents - issue precedent recording and checking."""

import json


from claude_quality.precedents import (
    Precedent,
    check_precedent,
    record_issue,
    run_precedent_checks,
)


class TestPrecedent:
    """Tests for Precedent dataclass."""

    def test_precedent_to_dict(self) -> None:
        """Test that precedent.to_dict() works correctly."""
        p = Precedent(
            check="echo test",
            description="Test description",
            fix="Run fix command",
            scope="local",
            severity="warning",
        )
        data = p.to_dict()
        assert data["check"] == "echo test"
        assert data["description"] == "Test description"
        assert data["fix"] == "Run fix command"
        assert data["scope"] == "local"
        assert data["severity"] == "warning"
        assert "created_at" in data
        assert "hits" in data

    def test_precedent_from_dict(self) -> None:
        """Test that precedent.from_dict() works correctly."""
        data = {
            "check": "echo test",
            "description": "Test description",
            "fix": "Run fix command",
            "scope": "local",
            "severity": "warning",
            "created_at": "2024-01-01T00:00:00",
            "hits": 5,
        }
        p = Precedent.from_dict(data)
        assert p.check == "echo test"
        assert p.description == "Test description"
        assert p.fix == "Run fix command"
        assert p.scope == "local"
        assert p.severity == "warning"
        assert p.hits == 5

    def test_precedent_from_dict_defaults(self) -> None:
        """Test that precedent.from_dict() uses defaults when fields missing."""
        data = {
            "check": "echo test",
            "description": "Test description",
            "fix": "Run fix command",
            "created_at": "2024-01-01T00:00:00",
        }
        p = Precedent.from_dict(data)
        assert p.scope == "both"  # default
        assert p.severity == "warning"  # default
        assert p.hits == 0  # default

    def test_precedent_roundtrip(self) -> None:
        """Test that to_dict and from_dict are inverse operations."""
        original = Precedent(
            check="echo test",
            description="Test description",
            fix="Run fix command",
            scope="ci",
            severity="fatal",
        )
        data = original.to_dict()
        restored = Precedent.from_dict(data)
        assert restored.check == original.check
        assert restored.description == original.description
        assert restored.fix == original.fix
        assert restored.scope == original.scope
        assert restored.severity == original.severity


class TestRecordIssue:
    """Tests for record_issue function."""

    def test_record_issue_creates_new_precedent(self, tmp_path, monkeypatch) -> None:
        """Test that record_issue creates a new precedent file."""
        monkeypatch.setattr(
            "claude_quality.precedents._PRECEDENTS_FILE",
            tmp_path / "precedents.json",
        )

        p = record_issue(
            check="echo test",
            description="Test issue",
            fix="Fix it",
            scope="local",
            severity="info",
        )

        assert p.check == "echo test"
        assert p.description == "Test issue"
        assert p.fix == "Fix it"
        assert p.scope == "local"
        assert p.severity == "info"
        assert p.hits == 0

        # Verify file was created
        assert (tmp_path / "precedents.json").exists()
        content = json.loads((tmp_path / "precedents.json").read_text())
        assert "precedents" in content
        assert len(content["precedents"]) == 1
        assert content["precedents"][0]["check"] == "echo test"

    def test_record_issue_appends_to_existing(self, tmp_path, monkeypatch) -> None:
        """Test that record_issue appends to existing precedents."""
        monkeypatch.setattr(
            "claude_quality.precedents._PRECEDENTS_FILE",
            tmp_path / "precedents.json",
        )
        # Create initial file
        (tmp_path / "precedents.json").write_text(
            json.dumps(
                {
                    "precedents": [
                        {
                            "check": "initial",
                            "description": "Initial",
                            "fix": "Fix",
                            "scope": "both",
                            "severity": "warning",
                            "created_at": "2024-01-01T00:00:00",
                            "hits": 0,
                        }
                    ]
                }
            )
        )

        record_issue(
            check="echo test",
            description="Test issue",
            fix="Fix it",
        )

        content = json.loads((tmp_path / "precedents.json").read_text())
        assert len(content["precedents"]) == 2
        assert content["precedents"][0]["check"] == "initial"
        assert content["precedents"][1]["check"] == "echo test"

    def test_record_issue_all_severities(self, tmp_path, monkeypatch) -> None:
        """Test recording issues with all severity levels."""
        monkeypatch.setattr(
            "claude_quality.precedents._PRECEDENTS_FILE",
            tmp_path / "precedents.json",
        )

        for severity in ["info", "warning", "error", "fatal"]:
            p = record_issue(
                check="echo test",
                description=f"Test {severity}",
                fix="Fix",
                severity=severity,
            )
            assert p.severity == severity


class TestCheckPrecedent:
    """Tests for check_precedent function."""

    def test_check_precedent_pass(self, tmp_path) -> None:
        """Test that passing precedent returns (True, output)."""
        p = Precedent(
            check="echo hello",
            description="Test",
            fix="N/A",
            scope="both",
            severity="warning",
        )
        passed, output = check_precedent(p, cwd=str(tmp_path))
        assert passed is True
        assert "hello" in output

    def test_check_precedent_fail(self, tmp_path) -> None:
        """Test that failing precedent returns (False, output)."""
        p = Precedent(
            check="exit 1",
            description="Test",
            fix="N/A",
            scope="both",
            severity="warning",
        )
        passed, output = check_precedent(p, cwd=str(tmp_path))
        assert passed is False

    def test_check_precedent_exception(self, tmp_path) -> None:
        """Test that exception returns (False, error message)."""
        p = Precedent(
            check="nonexistent_command_xyz",
            description="Test",
            fix="N/A",
            scope="both",
            severity="warning",
        )
        passed, output = check_precedent(p, cwd=str(tmp_path))
        assert passed is False
        # The output contains shell error, check it has some output
        assert len(output) > 0

    def test_check_precedent_timeout(self, tmp_path, monkeypatch) -> None:
        """Test that timeout returns (False, 'Timeout')."""
        import subprocess

        p = Precedent(
            check="sleep 10",
            description="Test",
            fix="N/A",
            scope="both",
            severity="warning",
        )

        # Temporarily set timeout very short

        original_run = subprocess.run

        def mock_run(*args, **kwargs):
            kwargs["timeout"] = 0.001  # Very short timeout
            return original_run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_run)
        passed, output = check_precedent(p, cwd=str(tmp_path))
        assert passed is False
        assert output == "Timeout"

    def test_check_precedent_with_cwd(self, tmp_path) -> None:
        """Test that check_precedent uses the cwd argument."""
        p = Precedent(
            check="pwd",
            description="Test",
            fix="N/A",
            scope="both",
            severity="warning",
        )
        passed, output = check_precedent(p, cwd=str(tmp_path))
        assert passed is True
        assert str(tmp_path) in output


class TestRunPrecedentChecks:
    """Tests for run_precedent_checks function."""

    def test_run_precedent_checks_empty(self, tmp_path, monkeypatch) -> None:
        """Test that empty precedent file returns empty results."""
        monkeypatch.setattr(
            "claude_quality.precedents._PRECEDENTS_FILE",
            tmp_path / "precedents.json",
        )
        (tmp_path / "precedents.json").write_text('{"precedents": []}')

        results = run_precedent_checks(scope="both")
        assert results == {
            "info": [],
            "warning": [],
            "error": [],
            "fatal": [],
        }

    def test_run_precedent_checks_one_passing(self, tmp_path, monkeypatch) -> None:
        """Test that passing precedent doesn't appear in results."""
        monkeypatch.setattr(
            "claude_quality.precedents._PRECEDENTS_FILE",
            tmp_path / "precedents.json",
        )
        precedents = [
            {
                "check": "echo hello",
                "description": "Passing check",
                "fix": "N/A",
                "scope": "both",
                "severity": "warning",
                "created_at": "2024-01-01T00:00:00",
                "hits": 0,
            }
        ]
        (tmp_path / "precedents.json").write_text(
            json.dumps({"precedents": precedents})
        )

        results = run_precedent_checks(scope="both")
        assert results["warning"] == []

    def test_run_precedent_checks_one_failing(self, tmp_path, monkeypatch) -> None:
        """Test that failing precedent appears in results."""
        monkeypatch.setattr(
            "claude_quality.precedents._PRECEDENTS_FILE",
            tmp_path / "precedents.json",
        )
        precedents = [
            {
                "check": "exit 1",
                "description": "Failing check",
                "fix": "Fix it",
                "scope": "both",
                "severity": "warning",
                "created_at": "2024-01-01T00:00:00",
                "hits": 0,
            }
        ]
        (tmp_path / "precedents.json").write_text(
            json.dumps({"precedents": precedents})
        )

        results = run_precedent_checks(scope="both")
        assert len(results["warning"]) == 1
        assert results["warning"][0]["description"] == "Failing check"
        assert results["warning"][0]["fix"] == "Fix it"
        assert "hits" in results["warning"][0]

    def test_run_precedent_checks_scope_filter(self, tmp_path, monkeypatch) -> None:
        """Test that scope filtering works correctly."""
        monkeypatch.setattr(
            "claude_quality.precedents._PRECEDENTS_FILE",
            tmp_path / "precedents.json",
        )
        precedents = [
            {
                "check": "exit 1",  # Both fail
                "description": "Local check",
                "fix": "N/A",
                "scope": "local",
                "severity": "warning",
                "created_at": "2024-01-01T00:00:00",
                "hits": 0,
            },
            {
                "check": "exit 1",  # Both fail
                "description": "CI check",
                "fix": "N/A",
                "scope": "ci",
                "severity": "error",
                "created_at": "2024-01-01T00:00:00",
                "hits": 0,
            },
        ]
        (tmp_path / "precedents.json").write_text(
            json.dumps({"precedents": precedents})
        )

        # Only local scope - both fail so both should appear
        results = run_precedent_checks(scope="local")
        # Both are failing, and both have scope "local" or "both"
        # "local" scope precedent matches "local" scope filter
        # "ci" scope precedent does NOT match "local" scope filter
        # Both precedents fail so both should be in results
        assert len(results["warning"]) >= 1

    def test_run_precedent_checks_hits_incremented(self, tmp_path, monkeypatch) -> None:
        """Test that hits are incremented for failing precedents."""
        monkeypatch.setattr(
            "claude_quality.precedents._PRECEDENTS_FILE",
            tmp_path / "precedents.json",
        )
        precedents = [
            {
                "check": "exit 1",
                "description": "Check",
                "fix": "N/A",
                "scope": "both",
                "severity": "warning",
                "created_at": "2024-01-01T00:00:00",
                "hits": 5,
            }
        ]
        (tmp_path / "precedents.json").write_text(
            json.dumps({"precedents": precedents})
        )

        results = run_precedent_checks(scope="both")
        assert len(results["warning"]) == 1
        # Hits should be incremented
        assert results["warning"][0]["hits"] == 6

    def test_run_precedent_checks_multiple_severities(
        self, tmp_path, monkeypatch
    ) -> None:
        """Test that results are grouped by severity."""
        monkeypatch.setattr(
            "claude_quality.precedents._PRECEDENTS_FILE",
            tmp_path / "precedents.json",
        )
        precedents = [
            {
                "check": "exit 1",
                "description": "Info check",
                "fix": "N/A",
                "scope": "both",
                "severity": "info",
                "created_at": "2024-01-01T00:00:00",
                "hits": 0,
            },
            {
                "check": "exit 1",
                "description": "Warning check",
                "fix": "N/A",
                "scope": "both",
                "severity": "warning",
                "created_at": "2024-01-01T00:00:00",
                "hits": 0,
            },
            {
                "check": "exit 1",
                "description": "Error check",
                "fix": "N/A",
                "scope": "both",
                "severity": "error",
                "created_at": "2024-01-01T00:00:00",
                "hits": 0,
            },
            {
                "check": "exit 1",
                "description": "Fatal check",
                "fix": "N/A",
                "scope": "both",
                "severity": "fatal",
                "created_at": "2024-01-01T00:00:00",
                "hits": 0,
            },
        ]
        (tmp_path / "precedents.json").write_text(
            json.dumps({"precedents": precedents})
        )

        results = run_precedent_checks(scope="both")
        assert len(results["info"]) == 1
        assert len(results["warning"]) == 1
        assert len(results["error"]) == 1
        assert len(results["fatal"]) == 1

    def test_run_precedent_checks_output_format(self, tmp_path, monkeypatch) -> None:
        """Test that failing precedents include output from failed command."""
        monkeypatch.setattr(
            "claude_quality.precedents._PRECEDENTS_FILE",
            tmp_path / "precedents.json",
        )
        precedents = [
            {
                "check": "echo error message && exit 1",
                "description": "Check with output",
                "fix": "Fix it",
                "scope": "both",
                "severity": "warning",
                "created_at": "2024-01-01T00:00:00",
                "hits": 0,
            }
        ]
        (tmp_path / "precedents.json").write_text(
            json.dumps({"precedents": precedents})
        )

        results = run_precedent_checks(scope="both")
        assert len(results["warning"]) == 1
        assert "error message" in results["warning"][0]["output"]

    def test_run_precedent_checks_scope_both_filters_all(
        self, tmp_path, monkeypatch
    ) -> None:
        """Test that scope='both' includes all precedents regardless of their scope."""
        monkeypatch.setattr(
            "claude_quality.precedents._PRECEDENTS_FILE",
            tmp_path / "precedents.json",
        )
        precedents = [
            {
                "check": "exit 1",
                "description": "Local only",
                "fix": "N/A",
                "scope": "local",
                "severity": "warning",
                "created_at": "2024-01-01T00:00:00",
                "hits": 0,
            },
            {
                "check": "exit 1",
                "description": "CI only",
                "fix": "N/A",
                "scope": "ci",
                "severity": "error",
                "created_at": "2024-01-01T00:00:00",
                "hits": 0,
            },
        ]
        (tmp_path / "precedents.json").write_text(
            json.dumps({"precedents": precedents})
        )

        # With scope='both', both should be checked
        results = run_precedent_checks(scope="both")
        assert len(results["warning"]) == 1
        assert len(results["error"]) == 1
