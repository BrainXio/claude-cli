# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-05-22

### Added

- Comprehensive test suite across `claude_cli`, `claude_knowledge`, and `claude_quality` packages (395 tests)
- `claude-check-model-vision` hook for detecting Ollama model vision capabilities
- `claude-standards-guard` PreToolUse hook blocking forbidden content in standards docs
- `claude-knowledge` CLI with ingest, compile, query, and validate subcommands
- `claude-dispatch` workflow dispatch engine
- `claude-statusline` statusline generator
- `claude-pre-commit` quality gate (ruff, mypy, pytest)
- Knowledge base pipeline: ingest markdown, compile daily logs, validate structure
- Quality gate system with modes (developer, research, review, ops, personal)
- Configurable allowed repos via `_config.get_allowed_repos()` with empty default

### Changed

- Refactored `check_model_vision` to output JSON to stdout only (removed file write)
- Refactored `standards_guard` to call `get_allowed_repos()` at runtime instead of hardcoded constant
- Moved data paths from `~/.brainxio/data/` to `~/.claude/data/`
- Bumped CI coverage threshold from 50% to 90%

### Fixed

- Fixed all ruff lint errors (F401, F811, F841)
- Fixed filesystem-dependent tests to use `tmp_path` instead of hardcoded paths
- Fixed test API mismatches after `ingest.py` refactor to factory functions
- Fixed CI failures in GitHub Actions runner environment

## Related Projects

- [BrainXio/claude-config](https://github.com/BrainXio/claude-config) — Framework configuration for `.claude/` settings, agents, rules, skills, and workflows
