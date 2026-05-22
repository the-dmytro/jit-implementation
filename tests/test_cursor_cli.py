import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jit_implementation.backends.cursor_cli import CursorCLIGenerationBackend
from jit_implementation.backends.generation import GenerationRequest
from jit_implementation.config import Settings
from jit_implementation.exceptions import CursorAgentError, CursorAgentNotFoundError


def _settings(**overrides) -> Settings:
    base = dict(
        provider="cursor",
        api_key=None,
        model="gpt-test",
        temperature=0.0,
        max_tries=5,
        cache_dir=Path(".jit_impl"),
        cursor_agent_bin="cursor-agent",
        cursor_api_key=None,
        workspace=Path("/tmp/ws"),
        cursor_timeout_seconds=30,
    )
    base.update(overrides)
    return Settings(**base)


def test_parse_stdout_direct_json():
    backend = CursorCLIGenerationBackend(_settings(), workspace=Path("/tmp/ws"))
    payload = backend._parse_stdout(
        json.dumps(
            {
                "imports": ["import math"],
                "code": "def f():\n    return 1",
                "chain_of_thought": ["step"],
            }
        )
    )
    assert payload["code"].startswith("def f")


def test_parse_stdout_fenced_json():
    backend = CursorCLIGenerationBackend(_settings(), workspace=Path("/tmp/ws"))
    stdout = 'Here is the result:\n```json\n{"imports": [], "code": "def g():\\n    pass", "chain_of_thought": []}\n```'
    payload = backend._parse_stdout(stdout)
    assert "def g" in payload["code"]


def test_build_prompt_includes_failure_feedback():
    backend = CursorCLIGenerationBackend(_settings(), workspace=Path("/tmp/ws"))
    prompt = backend._build_prompt(
        GenerationRequest(
            instructions="sys",
            stub_source="def foo(): ...",
            related_sources={"Bar": "class Bar: pass"},
            failure_feedback="tests failed",
        )
    )
    assert "def foo" in prompt
    assert "class Bar" in prompt
    assert "tests failed" in prompt
    assert "Do not edit" in prompt or "JSON" in prompt


@patch("jit_implementation.backends.cursor_cli.shutil.which", return_value=None)
def test_missing_binary_raises(mock_which):
    backend = CursorCLIGenerationBackend(_settings(), workspace=Path("/tmp/ws"))
    with pytest.raises(CursorAgentNotFoundError):
        backend.generate(
            GenerationRequest(
                instructions="x",
                stub_source="def a(): ...",
                related_sources={},
            )
        )


@patch("jit_implementation.backends.cursor_cli.shutil.which", return_value="/bin/cursor-agent")
@patch("jit_implementation.backends.cursor_cli.subprocess.run")
def test_generate_success(mock_run, mock_which):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps(
            {
                "imports": [],
                "code": "def answer():\n    return 42",
                "chain_of_thought": [],
            }
        ),
        stderr="",
    )
    backend = CursorCLIGenerationBackend(_settings(), workspace=Path("/tmp/ws"))
    result = backend.generate(
        GenerationRequest(
            instructions="implement",
            stub_source="def answer(): ...",
            related_sources={},
        )
    )
    assert "return 42" in result.code
    command = mock_run.call_args[0][0]
    assert command[0] == "/bin/cursor-agent"
    assert "--output-format" in command
    assert "json" in command


@patch("jit_implementation.backends.cursor_cli.shutil.which", return_value="/bin/cursor-agent")
@patch("jit_implementation.backends.cursor_cli.subprocess.run")
def test_generate_nonzero_exit(mock_run, mock_which):
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="auth failed")
    backend = CursorCLIGenerationBackend(_settings(), workspace=Path("/tmp/ws"))
    with pytest.raises(CursorAgentError, match="exited with code 1"):
        backend.generate(
            GenerationRequest(
                instructions="x",
                stub_source="def a(): ...",
                related_sources={},
            )
        )
