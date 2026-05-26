"""Tests for claude_cli._hook_metrics."""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from claude_cli._hook_metrics import (
    fetch_with_backoff,
    log_metric,
    timed_hook,
)


class TestLogMetric:
    """Tests for log_metric."""

    def test_appends_structured_line(self, tmp_path: Path) -> None:
        """log_metric writes a JSON line to the metrics file."""
        metric_file = tmp_path / "hook_metrics.jsonl"
        with patch("claude_cli._hook_metrics.METRICS_PATH", metric_file):
            log_metric("test_hook", 12.34, True)

        lines = metric_file.read_text().strip().split("\n")
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["hook"] == "test_hook"
        assert record["duration_ms"] == 12.34
        assert record["success"] is True
        assert "ts" in record

    def test_includes_error_type(self, tmp_path: Path) -> None:
        """log_metric records error_type when provided."""
        metric_file = tmp_path / "hook_metrics.jsonl"
        with patch("claude_cli._hook_metrics.METRICS_PATH", metric_file):
            log_metric("test_hook", 1.0, False, error_type="ValueError")

        record = json.loads(metric_file.read_text().strip().split("\n")[0])
        assert record["error_type"] == "ValueError"

    def test_includes_extra_fields(self, tmp_path: Path) -> None:
        """log_metric merges extra dict into the record."""
        metric_file = tmp_path / "hook_metrics.jsonl"
        with patch("claude_cli._hook_metrics.METRICS_PATH", metric_file):
            log_metric("test_hook", 1.0, True, extra={"model": "llava"})

        record = json.loads(metric_file.read_text().strip().split("\n")[0])
        assert record["model"] == "llava"


class TestTimedHook:
    """Tests for timed_hook context manager."""

    def test_logs_success(self, tmp_path: Path) -> None:
        """timed_hook logs success when body completes."""
        metric_file = tmp_path / "hook_metrics.jsonl"
        with patch("claude_cli._hook_metrics.METRICS_PATH", metric_file):
            with timed_hook("my_hook"):
                pass

        record = json.loads(metric_file.read_text().strip().split("\n")[0])
        assert record["hook"] == "my_hook"
        assert record["success"] is True
        assert record["duration_ms"] >= 0

    def test_logs_failure(self, tmp_path: Path) -> None:
        """timed_hook logs failure when body raises."""
        metric_file = tmp_path / "hook_metrics.jsonl"
        with patch("claude_cli._hook_metrics.METRICS_PATH", metric_file):
            with pytest.raises(RuntimeError):
                with timed_hook("fail_hook"):
                    raise RuntimeError("boom")

        record = json.loads(metric_file.read_text().strip().split("\n")[0])
        assert record["hook"] == "fail_hook"
        assert record["success"] is False
        assert record["error_type"] == "RuntimeError"


class TestFetchWithBackoff:
    """Tests for fetch_with_backoff."""

    def test_returns_body_on_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """fetch_with_backoff returns response bytes on success."""

        class FakeResp:
            def read(self) -> bytes:
                return b'{"models":[]}'

            def __enter__(self) -> "FakeResp":
                return self

            def __exit__(self, *args: object) -> None:
                pass

        monkeypatch.setattr(
            "claude_cli._hook_metrics.urllib.request.urlopen",
            lambda req, timeout: FakeResp(),
        )
        result = fetch_with_backoff("http://localhost:11434/api/tags")
        assert result == b'{"models":[]}'

    def test_raises_on_non_429_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """fetch_with_backoff raises immediately on non-429 HTTP errors."""
        import urllib.request

        exc = urllib.request.HTTPError(
            "http://localhost/api/tags",
            500,
            "Internal Server Error",
            {},
            None,
        )
        monkeypatch.setattr(
            "claude_cli._hook_metrics.urllib.request.urlopen",
            lambda req, timeout: (_ for _ in ()).throw(exc),
        )
        with pytest.raises(urllib.request.HTTPError) as ctx:
            fetch_with_backoff("http://localhost/api/tags")
        assert ctx.value.code == 500

    def test_backoff_on_429(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """fetch_with_backoff retries with exponential backoff on 429."""
        import urllib.request

        class FakeResp:
            def read(self) -> bytes:
                return b'ok'

            def __enter__(self) -> "FakeResp":
                return self

            def __exit__(self, *args: object) -> None:
                pass

        calls: list[int] = []
        exc429 = urllib.request.HTTPError(
            "http://localhost/api/tags",
            429,
            "Too Many Requests",
            {},
            None,
        )

        def side_effect(req: object, timeout: float) -> FakeResp:
            calls.append(1)
            if len(calls) < 2:
                raise exc429
            return FakeResp()

        monkeypatch.setattr(
            "claude_cli._hook_metrics.urllib.request.urlopen",
            side_effect,
        )

        start = time.perf_counter()
        result = fetch_with_backoff("http://localhost/api/tags", base_delay=0.05)
        elapsed = time.perf_counter() - start

        assert result == b"ok"
        assert len(calls) == 2
        assert elapsed >= 0.05  # at least one backoff delay
