import os
from dataclasses import dataclass
from pathlib import Path


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


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    model: str
    temperature: float
    max_tries: int
    cache_dir: Path

    @classmethod
    def from_env(cls, *, max_tries: int | None = None) -> "Settings":
        return cls(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("JIT_IMPLEMENTATION_MODEL", "gpt-4.1"),
            temperature=_env_float("JIT_IMPLEMENTATION_TEMPERATURE", 0.0),
            max_tries=max_tries if max_tries is not None else _env_int("JIT_IMPLEMENTATION_MAX_TRIES", 5),
            cache_dir=Path(os.getenv("JIT_IMPLEMENTATION_CACHE_DIR", ".jit_impl")),
        )


DEFAULT_SETTINGS = Settings.from_env()
