from pathlib import Path
from unittest.mock import MagicMock

from jit_implementation.backends.cursor_cli import CursorCLIGenerationBackend
from jit_implementation.backends.factory import create_generation_backend
from jit_implementation.backends.openai_generation import OpenAIGenerationBackend
from jit_implementation.config import Settings


def test_factory_openai_default():
    settings = Settings(
        provider="openai",
        api_key="x",
        model="gpt-test",
        temperature=0.0,
        max_tries=5,
        cache_dir=Path(".jit_impl"),
        cursor_agent_bin="cursor-agent",
        cursor_api_key=None,
        workspace=None,
        cursor_timeout_seconds=300,
        cursor_batch_timeout_seconds=600,
    )
    backend = create_generation_backend(settings, ide=MagicMock())
    assert isinstance(backend, OpenAIGenerationBackend)


def test_factory_cursor(tmp_path):
    settings = Settings(
        provider="cursor",
        api_key=None,
        model="gpt-test",
        temperature=0.0,
        max_tries=5,
        cache_dir=Path(".jit_impl"),
        cursor_agent_bin="cursor-agent",
        cursor_api_key=None,
        workspace=tmp_path,
        cursor_timeout_seconds=300,
        cursor_batch_timeout_seconds=600,
    )
    decl = tmp_path / "mod.py"
    decl.write_text("def f(): ...\n")
    backend = create_generation_backend(
        settings, ide=MagicMock(), declaration_file=decl
    )
    assert isinstance(backend, CursorCLIGenerationBackend)
