# ADR-005: Reference > Duplicate for Multi-Repo Documentation

## Status

Accepted

## Context

Each repository maintained its own copy of org-wide conventions (branch naming, commit style, security rules). These copies diverged silently, creating conflicting instructions for contributors.

## Decision

Establish a documentation hierarchy:

- **Org-wide conventions** live in `BrainXio/.github/CONTRIBUTING.md` (one source of truth)
- **Repo-specific docs** (local `CONTRIBUTING.md`, `README.md`) link to the org-wide doc for shared rules and add only domain-specific content
- **Cross-repo links** use plain text references (`BrainXio/.github/CONTRIBUTING.md`) to avoid triggering the standards guard

Every local `CONTRIBUTING.md` must be >50% repo-specific content by line count.

## Consequences

- **Positive**: Org-wide policy changes update one file
- **Positive**: Contributors see consistent instructions across all repos
- **Negative**: Requires discipline to not copy-paste org-wide content into local docs
