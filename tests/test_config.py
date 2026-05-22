import os

from jit_implementation.config import Settings


def test_settings_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("JIT_IMPLEMENTATION_MODEL", "gpt-test")
    monkeypatch.setenv("JIT_IMPLEMENTATION_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("JIT_IMPLEMENTATION_MAX_TRIES", "3")

    settings = Settings.from_env()

    assert settings.api_key == "test-key"
    assert settings.model == "gpt-test"
    assert settings.max_tries == 3
    assert settings.cache_dir == tmp_path / "cache"
