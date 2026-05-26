from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jit_implementation import implement, implement_batch
from jit_implementation.backends.generation import GenerationResult
from jit_implementation.batch import BatchRegistry


@pytest.fixture(autouse=True)
def clear_registry():
    BatchRegistry._groups.clear()
    yield
    BatchRegistry._groups.clear()


def test_implement_batch_registers_stub(tmp_path, monkeypatch):
    monkeypatch.setenv("JIT_IMPLEMENTATION_PROVIDER", "cursor")
    monkeypatch.setenv("JIT_IMPLEMENTATION_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("JIT_IMPLEMENTATION_WORKSPACE", str(tmp_path))

    batch_result = {
        "add_one": GenerationResult(
            imports=[],
            code="def add_one(x: int) -> int:\n    return x + 1",
            chain_of_thought=[],
        ),
        "double": GenerationResult(
            imports=[],
            code="def double(x: int) -> int:\n    return x * 2",
            chain_of_thought=[],
        ),
    }

    @implement_batch("ops", provider="cursor")
    @implement(provider="cursor")
    def add_one(x: int) -> int:
        """Add one."""
        ...

    @implement_batch("ops", provider="cursor")
    @implement(provider="cursor")
    def double(x: int) -> int:
        """Double."""
        ...

    mock_backend = MagicMock()
    mock_backend.generate_batch.return_value = batch_result

    with patch(
        "jit_implementation.batch.create_generation_backend",
        return_value=mock_backend,
    ):
        assert add_one(2) == 3
        assert mock_backend.generate_batch.call_count == 1
        assert double(3) == 6
        assert mock_backend.generate_batch.call_count == 1

    group = BatchRegistry.get_group("ops")
    assert group is not None
    assert set(group.members) == {"add_one", "double"}
