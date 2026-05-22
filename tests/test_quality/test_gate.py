"""Tests for claude_quality.gate - quality gate enforcement."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from claude_quality.gate import run_ci_gate, run_quality_gate


class TestRunQualityGate:
    """Tests for run_quality_gate function."""

    def test_secrets_scan_passes(self, monkeypatch) -> None:
        """Test that secrets scan passing sets results['secrets'] = True."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        def mock_subprocess_run(*args, **kwargs):
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        results = run_quality_gate(fast=True)
        assert results["secrets"] is True

    def test_secrets_scan_fails(self, monkeypatch) -> None:
        """Test that secrets scan failing sets results['secrets'] = False."""
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.CalledProcessError(1, ["gitleaks"])),
        )

        results = run_quality_gate(fast=True)
        assert results["secrets"] is False

    def test_secrets_file_not_found(self, monkeypatch) -> None:
        """Test that FileNotFoundError sets results['secrets'] = False."""
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()),
        )

        results = run_quality_gate(fast=True)
        assert results["secrets"] is False

    def test_secrets_timeout(self, monkeypatch) -> None:
        """Test that TimeoutExpired sets results['secrets'] = False."""
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("timeout", None)),
        )

        results = run_quality_gate(fast=True)
        assert results["secrets"] is False

    def test_ruff_check_passes(self, monkeypatch) -> None:
        """Test that ruff check passing sets results['ruff'] = True."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        def mock_subprocess_run(*args, **kwargs):
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        results = run_quality_gate(files=["test.py"], fast=True)
        assert results["secrets"] is True
        assert results["ruff"] is True

    def test_ruff_check_fails(self, monkeypatch) -> None:
        """Test that ruff check failing sets results['ruff'] = False."""
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.CalledProcessError(1, ["ruff"])),
        )

        results = run_quality_gate(files=["test.py"], fast=True)
        assert results["ruff"] is False

    def test_mypy_check_passes(self, monkeypatch) -> None:
        """Test that mypy check passing sets results['mypy'] = True."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        def mock_subprocess_run(*args, **kwargs):
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        results = run_quality_gate(fast=False)
        assert results["mypy"] is True

    def test_mypy_check_fails(self, monkeypatch) -> None:
        """Test that mypy check failing sets results['mypy'] = False."""
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.CalledProcessError(1, ["mypy"])),
        )

        results = run_quality_gate(fast=False)
        assert results["mypy"] is False

    def test_default_files_for_ruff(self, monkeypatch) -> None:
        """Test that default files includes current directory."""
        called_targets = []

        def mock_subprocess_run(*args, **kwargs):
            called_targets.extend(args[0])
            return MagicMock(returncode=0)

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
        run_quality_gate(fast=True)
        assert "." in called_targets

    def test_custom_files_for_ruff(self, monkeypatch) -> None:
        """Test that custom files are passed to ruff check."""
        called_targets = []

        def mock_subprocess_run(*args, **kwargs):
            called_targets.extend(args[0])
            return MagicMock(returncode=0)

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
        run_quality_gate(files=["src/", "tests/"], fast=True)
        assert "src/" in called_targets
        assert "tests/" in called_targets

    def test_quality_gate_fast_vs_slow(self, monkeypatch) -> None:
        """Test that fast mode skips mypy check."""
        check_types = []

        def mock_subprocess_run(*args, **kwargs):
            check_types.append(args[0][0])
            return MagicMock(returncode=0)

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        # Fast mode - should NOT call mypy
        run_quality_gate(fast=True)
        assert "mypy" not in check_types

        # Slow mode - should call mypy
        check_types.clear()
        run_quality_gate(fast=False)
        assert "mypy" in check_types


class TestRunCiGate:
    """Tests for run_ci_gate function."""

    def test_ci_gate_all_pass(self, monkeypatch) -> None:
        """Test that all CI checks passing returns True for all."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        def mock_subprocess_run(*args, **kwargs):
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        results = run_ci_gate()
        assert results["ruff"] is True
        assert results["format"] is True
        assert results["mypy"] is True
        assert results["pytest"] is True
        assert results["build"] is True

    def test_ci_gate_ruff_fails(self, monkeypatch) -> None:
        """Test that ruff failure sets results['ruff'] = False."""
        call_count = 0

        def mock_subprocess_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # First call is ruff
                raise subprocess.CalledProcessError(1, ["ruff"])
            return MagicMock(returncode=0)

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        results = run_ci_gate()
        assert results["ruff"] is False

    def test_ci_gate_format_fails(self, monkeypatch) -> None:
        """Test that format check failure sets results['format'] = False."""
        call_count = 0

        def mock_subprocess_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Second call is format
                raise subprocess.CalledProcessError(1, ["ruff", "format"])
            return MagicMock(returncode=0)

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        results = run_ci_gate()
        assert results["format"] is False

    def test_ci_gate_mypy_fails(self, monkeypatch) -> None:
        """Test that mypy failure sets results['mypy'] = False."""
        call_count = 0

        def mock_subprocess_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 3:  # Third call is mypy
                raise subprocess.CalledProcessError(1, ["mypy"])
            return MagicMock(returncode=0)

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        results = run_ci_gate()
        assert results["mypy"] is False

    def test_ci_gate_pytest_fails(self, monkeypatch) -> None:
        """Test that pytest failure sets results['pytest'] = False."""
        call_count = 0

        def mock_subprocess_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 4:  # Fourth call is pytest
                raise subprocess.CalledProcessError(1, ["pytest"])
            return MagicMock(returncode=0)

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        results = run_ci_gate()
        assert results["pytest"] is False

    def test_ci_gate_build_fails(self, monkeypatch) -> None:
        """Test that build failure sets results['build'] = False."""
        call_count = 0

        def mock_subprocess_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 5:  # Fifth call is build
                raise subprocess.CalledProcessError(1, ["python", "-m", "build"])
            return MagicMock(returncode=0)

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        results = run_ci_gate()
        assert results["build"] is False

    def test_ci_gate_with_custom_paths(self, monkeypatch) -> None:
        """Test that custom paths are passed to CI checks."""
        called_args = []

        def mock_subprocess_run(*args, **kwargs):
            called_args.append(args[0])
            return MagicMock(returncode=0)

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
        run_ci_gate(src_path="custom_src", test_path="custom_tests")

        # Check mypy uses custom src path
        mypy_args = [args for args in called_args if "mypy" in args]
        assert mypy_args
        assert "custom_src" in mypy_args[0]

        # Check pytest uses custom test path
        pytest_args = [args for args in called_args if "pytest" in args]
        assert pytest_args
        assert "custom_tests" in pytest_args[0]

    def test_ci_gate_file_not_found(self, monkeypatch) -> None:
        """Test that FileNotFoundError sets results entry to False."""
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()),
        )

        results = run_ci_gate()
        assert results["ruff"] is False
        assert results["format"] is False
        assert results["mypy"] is False
        assert results["pytest"] is False
        assert results["build"] is False

    def test_ci_gate_timeout(self, monkeypatch) -> None:
        """Test that TimeoutExpired sets results entry to False."""
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("timeout", None)),
        )

        results = run_ci_gate()
        assert results["ruff"] is False

    def test_ci_gate_check_order(self, monkeypatch) -> None:
        """Test that CI checks run in expected order."""
        call_order = []

        def mock_subprocess_run(*args, **kwargs):
            call_order.append(args[0][0])
            return MagicMock(returncode=0)

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
        run_ci_gate()

        # Check order is correct: ruff, format, mypy, pytest, build
        assert call_order[0] == "ruff"  # First is ruff check
        assert call_order[1] == "ruff"  # Second is format check (also starts with ruff)
        assert "mypy" in call_order
        assert "pytest" in call_order
        # Build check starts with python
        assert "python" in call_order[-1]  # Last call should be build

    def test_ci_gate_custom_paths_in_build(self, monkeypatch) -> None:
        """Test that custom src path is passed to mypy in build check."""
        called_args = []

        def mock_subprocess_run(*args, **kwargs):
            called_args.append(args[0])
            return MagicMock(returncode=0)

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
        run_ci_gate(src_path="custom_src", test_path="custom_tests")

        # Find mypy call
        mypy_calls = [args for args in called_args if "mypy" in args]
        assert mypy_calls
        assert "custom_src" in mypy_calls[0]
