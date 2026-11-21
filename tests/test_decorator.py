import jit_implementation.decorator as decorator_module
from jit_implementation import implement


class FakeCoder:
    captured: dict = {}

    def __init__(
        self, obj, test_functions, autonomous, in_place, max_tries, model=None
    ):
        FakeCoder.captured = {
            "obj": obj,
            "test_functions": test_functions,
            "autonomous": autonomous,
            "in_place": in_place,
            "max_tries": max_tries,
            "model": model,
        }

    def run(self):
        return lambda a, b=0: a + b


def test_implement_plain_decorator(monkeypatch):
    monkeypatch.setattr(decorator_module, "Coder", FakeCoder)

    @implement
    def add(a, b=0): ...

    assert add.__name__ == "add"
    assert add(2, b=3) == 5
    assert FakeCoder.captured["autonomous"] is True
    assert FakeCoder.captured["max_tries"] == 5
    assert FakeCoder.captured["model"] is None


def test_implement_with_options(monkeypatch):
    monkeypatch.setattr(decorator_module, "Coder", FakeCoder)
    tests = [lambda f: (True, "ok")]

    @implement(test_functions=tests, autonomous=False, max_tries=2, model="my-model")
    def add(a, b=0): ...

    assert add(1, 2) == 3
    assert FakeCoder.captured["test_functions"] is tests
    assert FakeCoder.captured["autonomous"] is False
    assert FakeCoder.captured["max_tries"] == 2
    assert FakeCoder.captured["model"] == "my-model"
