import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from jit_implementation import implement, implement_batch


def _cursor_available() -> bool:
    if shutil.which("cursor-agent") is None:
        return False
    if os.getenv("CURSOR_API_KEY"):
        return True
    try:
        completed = subprocess.run(
            ["cursor-agent", "status"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return completed.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


pytestmark = pytest.mark.integration


@pytest.mark.skipif(not _cursor_available(), reason="cursor-agent not available")
def test_cursor_json_probe():
    completed = subprocess.run(
        [
            "cursor-agent",
            "-p",
            "--output-format",
            "json",
            "--trust",
            'Return ONLY JSON: {"ok": true}',
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    stdout = (completed.stdout or "").strip()
    assert stdout
    payload = json.loads(stdout) if stdout.startswith("{") else json.loads(
        stdout[stdout.find("{") : stdout.rfind("}") + 1]
    )
    assert payload.get("ok") is True or "ok" in str(payload)


@pytest.mark.skipif(not _cursor_available(), reason="cursor-agent not available")
def test_batch_two_stubs_live(tmp_path, monkeypatch):
    monkeypatch.setenv("JIT_IMPLEMENTATION_PROVIDER", "cursor")
    monkeypatch.setenv("JIT_IMPLEMENTATION_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("JIT_IMPLEMENTATION_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("JIT_IMPLEMENTATION_MAX_TRIES", "2")

    @implement_batch("live_math", provider="cursor")
    @implement(provider="cursor")
    def fib(n: int) -> int:
        """Return nth Fibonacci number (0-indexed: fib(0)=0, fib(1)=1)."""
        ...

    @implement_batch("live_math", provider="cursor")
    @implement(provider="cursor")
    def factorial(n: int) -> int:
        """Return n! for n >= 0."""
        ...

    assert fib(10) == 55
    assert factorial(5) == 120
