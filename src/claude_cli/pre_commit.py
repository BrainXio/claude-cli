"""claude-pre-commit -- pre-commit validation with auto-fix.

Auto-fixes: ruff format, ruff check --fix, mdformat
Blocks on: mypy strict failures
Exits 0 on success.
"""

import subprocess
import sys


def main() -> None:
    for cmd, desc in [
        (["uv", "run", "ruff", "format", "src/"], "ruff format"),
        (["uv", "run", "ruff", "check", "--fix", "src/"], "ruff check --fix"),
        (["uv", "run", "mdformat", "."], "mdformat"),
    ]:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if "reformatted" in r.stdout or "fixed" in r.stdout:
            print(f"  {desc}: FIXED")
        elif r.returncode == 0:
            print(f"  {desc}: OK")

    r = subprocess.run(
        ["uv", "run", "mypy", "src/claude_cli/", "--strict"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(f"  mypy: FAIL\n{r.stdout}{r.stderr}")
        print("Pre-commit blocked: mypy errors.")
        sys.exit(1)
    print("  mypy: OK")

    sys.exit(0)


if __name__ == "__main__":
    main()
