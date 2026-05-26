# ADR-003: Gitleaks Secret Scanning Integration

## Status

Accepted

## Context

No secret scanning existed in the workspace. CI did not enforce secret detection, and local development had no protection against accidentally committing credentials.

## Decision

Integrate gitleaks at three levels:

1. **Repo config**: `.gitleaks.toml` with project-specific allowlists for false positives (test data, dummy keys)
1. **Pre-commit hook**: `.githooks/pre-commit` runs `gitleaks protect --staged`
1. **CI gate**: `cicd/.github/workflows/ci-python.yml` adds `gitleaks detect` step

The `.gitleaks.toml` must be tuned to exclude common false positives so developers do not ignore real alerts.

## Consequences

- **Positive**: Secrets are caught at commit time (local) and at merge time (CI)
- **Positive**: False-positive tuning prevents alert fatigue
- **Negative**: Requires `GITLEAKS_LICENSE` secret in CI
