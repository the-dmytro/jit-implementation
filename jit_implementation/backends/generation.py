from dataclasses import dataclass
from typing import Protocol


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


class GenerationBackend(Protocol):
    def generate(self, request: GenerationRequest) -> GenerationResult: ...
