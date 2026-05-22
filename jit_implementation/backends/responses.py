from typing import Any

import openai
from openai import OpenAI

from jit_implementation.backends.protocol import AgentStep, ParsedToolCall


class ResponsesBackend:
    def __init__(
        self,
        client: OpenAI,
        *,
        model: str,
        temperature: float,
    ) -> None:
        self._client = client
        self._model = model
        self._temperature = temperature
        self._instructions = ""
        self._input_items: list[Any] = []

    def begin(self, *, instructions: str, user_content: str) -> None:
        self._instructions = instructions
        self._input_items = [
            {
                "role": "user",
                "content": user_content,
            }
        ]

    def complete_with_tools(self, tools: list[Any]) -> AgentStep:
        try:
            response = self._client.responses.parse(
                model=self._model,
                instructions=self._instructions,
                input=self._input_items,
                tools=tools,
                tool_choice="required",
                temperature=self._temperature,
            )
        except Exception as exc:
            if exc.__class__.__name__ == "ContentFormatError":
                raise RuntimeError(
                    "OpenAI returned tool arguments that did not match the expected schema."
                ) from exc
            raise

        self._input_items.extend(response.output)

        tool_calls: list[ParsedToolCall] = []
        for item in response.output:
            if item.type != "function_call":
                continue
            tool_calls.append(
                ParsedToolCall(
                    call_id=item.call_id,
                    name=item.name,
                    parsed_arguments=item.parsed_arguments,
                )
            )

        return AgentStep(tool_calls=tool_calls, raw_output=list(response.output))

    def submit_tool_result(self, call_id: str, output: str) -> None:
        self._input_items.append(
            {
                "type": "function_call_output",
                "call_id": call_id,
                "output": output,
            }
        )
