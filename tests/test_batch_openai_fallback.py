from pathlib import Path
from unittest.mock import MagicMock, patch

from jit_implementation.backends.generation import BatchGenerationRequest, StubSpec
from jit_implementation.backends.openai_generation import OpenAIGenerationBackend
from jit_implementation.config import Settings


def test_openai_generate_batch_calls_generate_per_stub():
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

    backend = OpenAIGenerationBackend(settings, ide=MagicMock())
    stub_a = StubSpec(name="a", obj=object(), stub_source="def a(): ...")
    stub_b = StubSpec(name="b", obj=object(), stub_source="def b(): ...")

    with patch.object(
        OpenAIGenerationBackend,
        "generate",
        side_effect=[
            MagicMock(imports=[], code="def a(): return 1", chain_of_thought=[]),
            MagicMock(imports=[], code="def b(): return 2", chain_of_thought=[]),
        ],
    ) as mock_generate:
        results = backend.generate_batch(
            BatchGenerationRequest(
                instructions="sys",
                stubs=[stub_a, stub_b],
                related_sources={},
            )
        )

    assert mock_generate.call_count == 2
    assert results["a"].code.startswith("def a")
    assert results["b"].code.startswith("def b")
