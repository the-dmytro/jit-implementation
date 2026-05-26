from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


@dataclass
class GenerationRequest:
    instructions: str
    stub_source: str
    related_sources: dict[str, str]
    failure_feedback: str | None = None


@dataclass
class GenerationResult:
    imports: list[str]
    code: str
    chain_of_thought: list[str]


@dataclass
class StubSpec:
    name: str
    obj: Any
    stub_source: str
    test_functions: list[Callable[[Any], tuple[bool, str]]] = field(
        default_factory=list
    )
    failure_feedback: str | None = None


@dataclass
class BatchGenerationRequest:
    instructions: str
    stubs: list[StubSpec]
    related_sources: dict[str, str]
    failure_feedback: dict[str, str] | None = None


class GenerationBackend(Protocol):
    def generate(self, request: GenerationRequest) -> GenerationResult: ...

    def generate_batch(
        self, request: BatchGenerationRequest
    ) -> dict[str, GenerationResult]: ...
