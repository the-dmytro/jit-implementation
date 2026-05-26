from typing import Any, Callable

import openai
from openai import OpenAI
from rich.console import Console

from jit_implementation.backends.generation import (
    BatchGenerationRequest,
    GenerationBackend,
    GenerationRequest,
    GenerationResult,

)
from jit_implementation.backends.responses import ResponsesBackend
from jit_implementation.config import Settings
from jit_implementation.exceptions import MissingAPIKeyError
from jit_implementation.ide import IDE
from jit_implementation.models import ReadSourceCode, Reasoning, SubmitVersion


class OpenAIGenerationBackend(GenerationBackend):
    def __init__(
        self,
        settings: Settings,
        *,
        ide: IDE,
        console: Console | None = None,
    ) -> None:
        self._settings = settings
        self._ide = ide
        self._console = console or Console()
        self._responses = ResponsesBackend(
            self._create_client(),
            model=settings.model,
            temperature=settings.temperature,
        )

    def _create_client(self) -> OpenAI:
        if not self._settings.api_key:
            raise MissingAPIKeyError()
        return OpenAI(api_key=self._settings.api_key)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        user_content = (
            "Implement the following function or class in Python.\n"
            "Please remember to separate imports and code as per instructions.\n"
            f"Function or class to implement:\n{request.stub_source}"
        )
        if request.related_sources:
            user_content += "\n\nRelated type sources are preloaded; use ReadSourceCode only if you need another type."
        if request.failure_feedback:
            user_content += f"\n\n{request.failure_feedback}"

        self._responses.begin(
            instructions=request.instructions,
            user_content=user_content,
        )

        chain_of_thought: list[str] = []
        type_by_name = {t.__name__: t for t in self._ide.unread_types}

        while True:
            step = self._responses.complete_with_tools(self._build_tools())
            submitted: GenerationResult | None = None

            for call in step.tool_calls:
                if call.name == "Reasoning" and isinstance(
                    call.parsed_arguments, Reasoning
                ):
                    chain_of_thought.extend(
                        call.parsed_arguments.chain_of_thought
                    )
                    self._responses.submit_tool_result(
                        call.call_id,
                        "Reasoning recorded. Continue with implementation.",
                    )

                elif call.name == "ReadSourceCode" and isinstance(
                    call.parsed_arguments, ReadSourceCode
                ):
                    type_name = call.parsed_arguments.type
                    if type_name not in type_by_name:
                        self._responses.submit_tool_result(
                            call.call_id,
                            f"Unknown type '{type_name}'. "
                            f"Available: {', '.join(type_by_name) or 'none'}.",
                        )
                        continue
                    source_code = self._ide.read_source(type_by_name[type_name])
                    self._responses.submit_tool_result(
                        call.call_id, source_code or ""
                    )

                elif call.name == "SubmitVersion" and isinstance(
                    call.parsed_arguments, SubmitVersion
                ):
                    implementation = call.parsed_arguments
                    submitted = GenerationResult(
                        imports=implementation.imports,
                        code=implementation.code,
                        chain_of_thought=chain_of_thought,
                    )
                    self._responses.submit_tool_result(
                        call.call_id, "Implementation received."
                    )

            if submitted is not None:
                return submitted

    def generate_batch(
        self, request: BatchGenerationRequest
    ) -> dict[str, GenerationResult]:
        results: dict[str, GenerationResult] = {}
        for stub in request.stubs:
            backend = OpenAIGenerationBackend(
                self._settings,
                ide=IDE(stub.obj),
                console=self._console,
            )
            results[stub.name] = backend.generate(
                GenerationRequest(
                    instructions=request.instructions,
                    stub_source=stub.stub_source,
                    related_sources=request.related_sources,
                    failure_feedback=stub.failure_feedback,
                )
            )
        return results

    def _build_tools(self) -> list[Any]:
        tools = [
            openai.pydantic_function_tool(SubmitVersion),
            openai.pydantic_function_tool(Reasoning),
        ]
        if self._ide.unread_types:
            tools.append(openai.pydantic_function_tool(ReadSourceCode))
        return tools
