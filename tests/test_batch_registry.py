import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jit_implementation.batch import BatchCoordinator, BatchRegistry
from jit_implementation.backends.generation import GenerationResult
from jit_implementation.config import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        provider="cursor",
        api_key=None,
        model="gpt-test",
        temperature=0.0,
        max_tries=5,
        cache_dir=tmp_path / "cache",
        cursor_agent_bin="cursor-agent",
        cursor_api_key=None,
        workspace=tmp_path,
        cursor_timeout_seconds=30,
        cursor_batch_timeout_seconds=600,
    )


@pytest.fixture(autouse=True)
def clear_registry():
    BatchRegistry._groups.clear()
    yield
    BatchRegistry._groups.clear()


def test_batch_lazy_single_cli_call(tmp_path):
    settings = _settings(tmp_path)

    def fib(n: int) -> int:
        """Return nth Fibonacci number."""
        ...

    def factorial(n: int) -> int:
        """Return n!."""
        ...

    fib._jit_batch_id = "math"  # type: ignore[attr-defined]
    factorial._jit_batch_id = "math"  # type: ignore[attr-defined]

    BatchRegistry.register(
        "math",
        fib,
        test_functions=None,
        autonomous=True,
        in_place=False,
        max_tries=5,
        settings=settings,
    )
    BatchRegistry.register(
        "math",
        factorial,
        test_functions=None,
        autonomous=True,
        in_place=False,
        max_tries=5,
        settings=settings,
    )

    batch_result = {
        "fib": GenerationResult(
            imports=[],
            code="def fib(n: int) -> int:\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a",
            chain_of_thought=[],
        ),
        "factorial": GenerationResult(
            imports=[],
            code="def factorial(n: int) -> int:\n    out = 1\n    for i in range(2, n + 1):\n        out *= i\n    return out",
            chain_of_thought=[],
        ),
    }

    mock_backend = MagicMock()
    mock_backend.generate_batch.return_value = batch_result

    with patch(
        "jit_implementation.batch.create_generation_backend",
        return_value=mock_backend,
    ):
        assert BatchCoordinator.ensure_implemented("math", fib)(10) == 55
        assert mock_backend.generate_batch.call_count == 1

        assert BatchCoordinator.ensure_implemented("math", factorial)(5) == 120
        assert mock_backend.generate_batch.call_count == 1


@patch("jit_implementation.backends.cursor_cli.shutil.which", return_value="/bin/cursor-agent")
@patch("jit_implementation.backends.cursor_cli.subprocess.run")
def test_cursor_batch_uses_batch_timeout(mock_run, mock_which, tmp_path):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps(
            {
                "implementations": {
                    "fib": {
                        "imports": [],
                        "code": "def fib(n: int) -> int:\n    return 1",
                        "chain_of_thought": [],
                    },
                    "factorial": {
                        "imports": [],
                        "code": "def factorial(n: int) -> int:\n    return 1",
                        "chain_of_thought": [],
                    },
                }
            }
        ),
        stderr="",
    )

    settings = _settings(tmp_path)

    def fib(n: int) -> int:
        ...

    def factorial(n: int) -> int:
        ...

    fib._jit_batch_id = "b"  # type: ignore[attr-defined]
    factorial._jit_batch_id = "b"  # type: ignore[attr-defined]

    for fn in (fib, factorial):
        BatchRegistry.register(
            "b",
            fn,
            test_functions=None,
            autonomous=True,
            in_place=False,
            max_tries=5,
            settings=settings,
        )

    BatchCoordinator.ensure_implemented("b", fib)
    cursor_calls = [
        c
        for c in mock_run.call_args_list
        if c.args and "cursor-agent" in str(c.args[0][0])
    ]
    assert cursor_calls
    assert cursor_calls[-1].kwargs["timeout"] == 600
