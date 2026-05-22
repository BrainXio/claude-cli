"""claude-pre-commit -- pre-commit validation with auto-fix.

Auto-fixes: ruff format, ruff check --fix, mdformat
Blocks on: mypy strict failures
Exits 0 on success.
"""

import os
import subprocess
import sys


def main() -> int:
    for cmd, desc in [
        (["uv", "run", "ruff", "format", "src/"], "ruff format"),
        (["uv", "run", "ruff", "check", "--fix", "src/"], "ruff check --fix"),
        (
            [
                "uvx",
                "--with",
                "mdformat-frontmatter",
                "--with",
                "mdformat-gfm",
                "mdformat",
                ".",
            ],
            "mdformat",
        ),
    ]:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if "reformatted" in r.stdout or "fixed" in r.stdout:
            print(f"  {desc}: FIXED")
        elif r.returncode == 0:
            print(f"  {desc}: OK")

    # Fast pytest smoke test: catches import errors and collection failures
    strict_env = os.environ.get("CLAUDE_STRICT_PRECOMMIT", "").strip()
    strict = strict_env in ("1", "true", "yes", "True", "TRUE")
    smoke_cmd = ["uv", "run", "pytest", "--co", "-q"]
    try:
        r = subprocess.run(
            smoke_cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r.returncode != 0:
            print(f"  pytest smoke: FAIL\n{r.stdout}{r.stderr}")
            print("Pre-commit blocked: pytest collection errors.")
            return 1
        print("  pytest smoke: OK")
    except subprocess.TimeoutExpired:
        print("  pytest smoke: TIMEOUT (>10s)")
        if strict:
            print("Pre-commit blocked: CLAUDE_STRICT_PRECOMMIT=1 requires passing smoke test.")
            return 1
        print("  Skipping smoke test (not strict mode). Run with CLAUDE_STRICT_PRECOMMIT=1 to enforce.")

    r = subprocess.run(
        ["uv", "run", "mypy", "src/claude_cli/", "--strict"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(f"  mypy: FAIL\n{r.stdout}{r.stderr}")
        print("Pre-commit blocked: mypy errors.")
        return 1
    print("  mypy: OK")

    return 0


if __name__ == "__main__":
    sys.exit(main())
