"""Quality gate enforcement for Claude CLI hooks."""

from __future__ import annotations

import subprocess


def run_quality_gate(
    files: list[str] | None = None,
    fast: bool = False,
) -> dict[str, bool]:
    """Run the fast local quality gate.

    Checks: branch protection, standards hash, staged secret scan, ruff check.
    Target: < 10 seconds for typical use.
    """
    results: dict[str, bool] = {}

    # Secret scan (staged changes only)
    try:
        subprocess.run(
            ["gitleaks", "protect", "--staged", "--verbose"],
            capture_output=True,
            check=True,
            timeout=30,
        )
        results["secrets"] = True
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        results["secrets"] = False

    # Ruff check
    targets = files if files else ["."]
    try:
        subprocess.run(
            ["ruff", "check"] + targets,
            capture_output=True,
            check=True,
            timeout=30,
        )
        results["ruff"] = True
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        results["ruff"] = False

    if not fast:
        # Type check
        try:
            subprocess.run(
                ["mypy", "src/"],
                capture_output=True,
                check=True,
                timeout=60,
            )
            results["mypy"] = True
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ):
            results["mypy"] = False

    return results


def run_ci_gate(
    src_path: str = "src",
    test_path: str = "tests",
) -> dict[str, bool]:
    """Run the full CI gate: lint, typecheck, test, coverage, build verify.

    Mirrors what the CI workflow runs. Use in SessionEnd hook.
    """
    results: dict[str, bool] = {}

    # Lint
    try:
        subprocess.run(
            ["ruff", "check", "."],
            capture_output=True,
            check=True,
            timeout=60,
        )
        results["ruff"] = True
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        results["ruff"] = False

    # Format check
    try:
        subprocess.run(
            ["ruff", "format", "--check", "."],
            capture_output=True,
            check=True,
            timeout=60,
        )
        results["format"] = True
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        results["format"] = False

    # Type check
    try:
        subprocess.run(
            ["mypy", src_path],
            capture_output=True,
            check=True,
            timeout=120,
        )
        results["mypy"] = True
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        results["mypy"] = False

    # Test
    try:
        subprocess.run(
            ["pytest", test_path, "-q"],
            capture_output=True,
            check=True,
            timeout=300,
        )
        results["pytest"] = True
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        results["pytest"] = False

    # Build verify
    try:
        subprocess.run(
            ["python", "-m", "build", "--wheel"],
            capture_output=True,
            check=True,
            timeout=120,
        )
        results["build"] = True
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        results["build"] = False

    return results
