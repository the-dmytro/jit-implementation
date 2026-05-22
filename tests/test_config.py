import os

import pytest

from jit_implementation.config import Settings


def test_settings_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("JIT_IMPLEMENTATION_MODEL", "gpt-test")
    monkeypatch.setenv("JIT_IMPLEMENTATION_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("JIT_IMPLEMENTATION_MAX_TRIES", "3")
    monkeypatch.setenv("JIT_IMPLEMENTATION_PROVIDER", "cursor")
    monkeypatch.setenv("CURSOR_AGENT_BIN", "cursor-agent-test")

    settings = Settings.from_env()

    assert settings.api_key == "test-key"
    assert settings.model == "gpt-test"
    assert settings.max_tries == 3
    assert settings.cache_dir == tmp_path / "cache"
    assert settings.provider == "cursor"
    assert settings.cursor_agent_bin == "cursor-agent-test"


def test_with_provider_override():
    base = Settings.from_env()
    updated = base.with_provider("cursor")
    assert updated.provider == "cursor"


def test_invalid_provider(monkeypatch):
    monkeypatch.setenv("JIT_IMPLEMENTATION_PROVIDER", "anthropic")
    with pytest.raises(ValueError, match="Unsupported"):
        Settings.from_env()
