from dataclasses import dataclass

from jit_implementation.backends.responses import ResponsesBackend
from jit_implementation.models import Reasoning


@dataclass
class FakeFunctionCall:
    type: str
    call_id: str
    name: str
    parsed_arguments: object


@dataclass
class FakeResponse:
    output: list


class FakeResponses:
    def __init__(self):
        self.calls: list[dict] = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return FakeResponse(
                output=[
                    FakeFunctionCall(
                        type="function_call",
                        call_id="call-1",
                        name="Reasoning",
                        parsed_arguments=Reasoning(
                            chain_of_thought=["think"]
                        ),
                    )
                ]
            )
        return FakeResponse(output=[])


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_responses_backend_accumulates_tool_outputs():
    backend = ResponsesBackend(FakeClient(), model="gpt-test", temperature=0.0)
    backend.begin(instructions="sys", user_content="implement foo")

    step = backend.complete_with_tools([])
    assert len(step.tool_calls) == 1
    assert step.tool_calls[0].name == "Reasoning"

    backend.submit_tool_result("call-1", "ok")
    backend.complete_with_tools([])

    client = backend._client
    assert client.responses.calls[1]["input"][-1] == {
        "type": "function_call_output",
        "call_id": "call-1",
        "output": "ok",
    }
