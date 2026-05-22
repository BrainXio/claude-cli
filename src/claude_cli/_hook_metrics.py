"""Lightweight hook metrics and rate-limiting utilities.

Logs structured metrics to hook_metrics.jsonl. Provides exponential
backoff for transient failures. Designed for zero perceptible latency
in the fast path.
"""

from __future__ import annotations

import json
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator


METRICS_PATH = Path.home() / ".claude" / "data" / "hook_metrics.jsonl"


def _ensure_metrics_dir() -> None:
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)


def log_metric(
    hook_name: str,
    duration_ms: float,
    success: bool,
    error_type: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Append a structured metric line to hook_metrics.jsonl."""
    _ensure_metrics_dir()
    record: dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hook": hook_name,
        "duration_ms": round(duration_ms, 2),
        "success": success,
    }
    if error_type:
        record["error_type"] = error_type
    if extra:
        record.update(extra)
    with open(METRICS_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


@contextmanager
def timed_hook(hook_name: str) -> Generator[None, None, None]:
    """Context manager that logs duration and success on exit."""
    start = time.perf_counter()
    try:
        yield
        elapsed = (time.perf_counter() - start) * 1000
        log_metric(hook_name, elapsed, True)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        log_metric(hook_name, elapsed, False, error_type=type(exc).__name__)
        raise


def fetch_with_backoff(
    url: str,
    max_retries: int = 3,
    base_delay: float = 0.5,
    timeout: float = 10.0,
) -> bytes:
    """Fetch URL with exponential backoff on HTTP 429.

    Returns response body as bytes. Raises last exception on exhaustion.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return bytes(resp.read())
        except urllib.request.HTTPError as exc:
            last_exc = exc
            if exc.code == 429 and attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                time.sleep(delay)
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("fetch_with_backoff exhausted retries unexpectedly")
