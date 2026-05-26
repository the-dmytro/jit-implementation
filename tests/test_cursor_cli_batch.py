import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jit_implementation.backends.cursor_cli import CursorCLIGenerationBackend
from jit_implementation.backends.generation import BatchGenerationRequest, StubSpec
from jit_implementation.config import Settings
from jit_implementation.exceptions import CursorAgentError


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
        cursor_batch_timeout_seconds=600,
    )
    base.update(overrides)
    return Settings(**base)


def test_build_batch_prompt_lists_stubs():
    backend = CursorCLIGenerationBackend(_settings(), workspace=Path("/tmp/ws"))
    prompt = backend._build_batch_prompt(
        BatchGenerationRequest(
            instructions="sys",
            stubs=[
                StubSpec(name="fib", obj=object(), stub_source="def fib(): ..."),
                StubSpec(name="factorial", obj=object(), stub_source="def factorial(): ..."),
            ],
            related_sources={},
            failure_feedback={"fib": "tests failed"},
        )
    )
    assert "fib" in prompt
    assert "factorial" in prompt
    assert "implementations" in prompt
    assert "tests failed" in prompt


@patch("jit_implementation.backends.cursor_cli.shutil.which", return_value="/bin/cursor-agent")
@patch("jit_implementation.backends.cursor_cli.subprocess.run")
def test_generate_batch_success(mock_run, mock_which):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps(
            {
                "implementations": {
                    "fib": {
                        "imports": [],
                        "code": "def fib(n: int) -> int:\n    return n",
                        "chain_of_thought": [],
                    },
                    "factorial": {
                        "imports": [],
                        "code": "def factorial(n: int) -> int:\n    return n",
                        "chain_of_thought": [],
                    },
                }
            }
        ),
        stderr="",
    )
    backend = CursorCLIGenerationBackend(_settings(), workspace=Path("/tmp/ws"))
    results = backend.generate_batch(
        BatchGenerationRequest(
            instructions="implement",
            stubs=[
                StubSpec(name="fib", obj=object(), stub_source="def fib(): ..."),
                StubSpec(
                    name="factorial", obj=object(), stub_source="def factorial(): ..."
                ),
            ],
            related_sources={},
        )
    )
    assert set(results) == {"fib", "factorial"}
    assert mock_run.call_args.kwargs["timeout"] == 600


@patch("jit_implementation.backends.cursor_cli.shutil.which", return_value="/bin/cursor-agent")
@patch("jit_implementation.backends.cursor_cli.subprocess.run")
def test_generate_batch_missing_key_raises(mock_run, mock_which):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps(
            {
                "implementations": {
                    "fib": {
                        "imports": [],
                        "code": "def fib(n: int) -> int:\n    return n",
                        "chain_of_thought": [],
                    }
                }
            }
        ),
        stderr="",
    )
    backend = CursorCLIGenerationBackend(_settings(), workspace=Path("/tmp/ws"))
    with pytest.raises(CursorAgentError, match="missing implementations"):
        backend.generate_batch(
            BatchGenerationRequest(
                instructions="x",
                stubs=[
                    StubSpec(name="fib", obj=object(), stub_source="def fib(): ..."),
                    StubSpec(
                        name="factorial", obj=object(), stub_source="def factorial(): ..."
                    ),
                ],
                related_sources={},
            )
        )
