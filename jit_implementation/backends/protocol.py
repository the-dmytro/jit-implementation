from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ParsedToolCall:
    call_id: str
    name: str
    parsed_arguments: Any


@dataclass(frozen=True)
class AgentStep:
    tool_calls: list[ParsedToolCall]
    raw_output: list[Any]


class LLMBackend(Protocol):
    def begin(self, *, instructions: str, user_content: str) -> None: ...

    def complete_with_tools(self, tools: list[Any]) -> AgentStep: ...

    def submit_tool_result(self, call_id: str, output: str) -> None: ...
