import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

Provider = Literal["openai", "cursor"]


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value)


def _parse_provider(value: str | None) -> Provider:
    if value is None or value == "openai":
        return "openai"
    if value == "cursor":
        return "cursor"
    raise ValueError(
        f"Unsupported JIT_IMPLEMENTATION_PROVIDER '{value}'. Use 'openai' or 'cursor'."
    )


@dataclass(frozen=True)
class Settings:
    provider: Provider
    api_key: str | None
    model: str
    temperature: float
    max_tries: int
    cache_dir: Path
    cursor_agent_bin: str
    cursor_api_key: str | None
    workspace: Path | None
    cursor_timeout_seconds: int
    cursor_batch_timeout_seconds: int

    @classmethod
    def from_env(
        cls,
        *,
        max_tries: int | None = None,
        provider: Provider | None = None,
    ) -> "Settings":
        return cls(
            provider=provider
            if provider is not None
            else _parse_provider(os.getenv("JIT_IMPLEMENTATION_PROVIDER")),
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("JIT_IMPLEMENTATION_MODEL", "gpt-4.1"),
            temperature=_env_float("JIT_IMPLEMENTATION_TEMPERATURE", 0.0),
            max_tries=max_tries
            if max_tries is not None
            else _env_int("JIT_IMPLEMENTATION_MAX_TRIES", 5),
            cache_dir=Path(os.getenv("JIT_IMPLEMENTATION_CACHE_DIR", ".jit_impl")),
            cursor_agent_bin=os.getenv("CURSOR_AGENT_BIN", "cursor-agent"),
            cursor_api_key=os.getenv("CURSOR_API_KEY"),
            workspace=(
                Path(ws)
                if (ws := os.getenv("JIT_IMPLEMENTATION_WORKSPACE"))
                else None
            ),
            cursor_timeout_seconds=_env_int(
                "JIT_IMPLEMENTATION_CURSOR_TIMEOUT", 300
            ),
            cursor_batch_timeout_seconds=_env_int(
                "JIT_IMPLEMENTATION_CURSOR_BATCH_TIMEOUT", 600
            ),
        )

    def with_provider(self, provider: Provider | None) -> "Settings":
        if provider is None:
            return self
        return replace(self, provider=provider)


DEFAULT_SETTINGS = Settings.from_env()
