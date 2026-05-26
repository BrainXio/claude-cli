"""Check vision capabilities for all configured Claude Code models.

Reads environment variables (ANTHROPIC_DEFAULT_*_MODEL, CLAUDE_CODE_SUBAGENT_MODEL)
and state.json to build a comprehensive capability map. Queries the local Ollama
instance via `ollama show` and falls back to known vision-capable model families.

Outputs JSON to stdout. Intended as a SessionStart hook.
"""

import datetime
import json
import os
import subprocess
from typing import Any

from ._hook_metrics import fetch_with_backoff, timed_hook
from ._llm import Provider


STATE_FILE = os.path.expanduser("~/.claude/data/state.json")

OLLAMA_URL = os.environ.get("ANTHROPIC_BASE_URL", "http://localhost:11434")
if OLLAMA_URL.endswith("/v1"):
    OLLAMA_URL = OLLAMA_URL[:-3]

# Known vision-capable remote model families (fallback when ollama show is silent)
KNOWN_VISION_REMOTES = {
    "kimi-k2.6",
    "kimi-k2",
    "qwen3.5",
    "qwen2.5-vl",
    "qwen2-vl",
    "llava",
    "bakllava",
    "moondream",
    "llama3.2-vision",
    "granite3.2-vision",
    "minicpm-v",
    "deepseek-vl",
}

# Environment variables that declare which models Claude Code may use
MODEL_ENV_VARS = [
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL",
]


class OllamaProvider:
    """Ollama-backed LLM provider."""

    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        self.base_url = base_url

    def list_models(self) -> list[dict[str, Any]]:
        """Return models from Ollama /api/tags."""
        try:
            body = fetch_with_backoff(f"{self.base_url}/api/tags", timeout=10)
            return json.loads(body).get("models", [])  # type: ignore
        except Exception:
            return []

    def show_model(self, model_name: str) -> tuple[str, bool]:
        """Run 'ollama show <model>' and return stdout text."""
        result = subprocess.run(
            ["ollama", "show", model_name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout, result.returncode == 0


def get_active_model() -> str | None:
    """Extract the active model identifier from state.json."""
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE) as f:
        state = json.load(f)
    mode_str = state.get("mode", {}).get("string", "")
    mode_str = mode_str if isinstance(mode_str, str) else None
    if not mode_str:
        return None
    # "Ollama-Cloud:deepseek-v4-pro:cloud" -> "deepseek-v4-pro:cloud"
    parts = mode_str.split(":")
    if len(parts) >= 3 and parts[0] == "Ollama-Cloud":
        return ":".join(parts[1:])
    return mode_str


def has_vision_capability(stdout: str) -> bool:
    """Check if ollama show output contains 'vision' in the Capabilities block."""
    in_caps = False
    for line in stdout.splitlines():
        stripped = line.rstrip()
        if stripped == "Capabilities":
            in_caps = True
            continue
        if in_caps:
            if not stripped.startswith(" "):
                break
            if stripped.strip() == "vision":
                return True
    return False


def check_model_vision(
    model_id: str | None, provider: Provider
) -> tuple[bool | None, str | None]:
    """Return (vision: bool|None, matched_model_name)."""
    if not model_id:
        return None, None

    stdout, ok = provider.show_model(model_id)
    if ok:
        return has_vision_capability(stdout), model_id

    model_base = model_id.split(":")[0]
    candidates = []
    for m in provider.list_models():
        name = m.get("name", "")
        remote = m.get("remote_model", "")
        if name == model_id or remote == model_base or remote == model_id:
            candidates.append(name)

    for cand in candidates:
        stdout, ok = provider.show_model(cand)
        if ok:
            caps = has_vision_capability(stdout)
            if caps:
                return True, cand

    for m in provider.list_models():
        remote = m.get("remote_model", "")
        if remote == model_base or remote == model_id:
            for vision_model in KNOWN_VISION_REMOTES:
                if vision_model in remote:
                    return True, m.get("name")
            return False, m.get("name")

    return None, None


def main() -> None:
    with timed_hook("check_model_vision"):
        _run_check()


def _run_check() -> None:
    provider = OllamaProvider(base_url=OLLAMA_URL)
    results = {}
    checked_models = set()

    for env_var in MODEL_ENV_VARS:
        model_id = os.environ.get(env_var)
        if not model_id:
            continue
        if model_id in checked_models:
            continue
        checked_models.add(model_id)
        vision, matched = check_model_vision(model_id, provider)
        results[env_var] = {
            "model": model_id,
            "vision": vision,
            "ollama_model": matched,
        }

    active_model = get_active_model()
    if active_model and active_model not in checked_models:
        vision, matched = check_model_vision(active_model, provider)
        results["__active__"] = {
            "model": active_model,
            "vision": vision,
            "ollama_model": matched,
        }

    any_vision = any(
        r.get("vision") for r in results.values() if r.get("vision") is not None
    )

    output = {
        "models": results,
        "any_vision_available": any_vision,
        "checked_at": datetime.datetime.now(datetime.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
