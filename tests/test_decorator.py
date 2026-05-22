from jit_implementation.decorator import implement


def test_function_decorator_uses_cached_implementation(monkeypatch):
    calls = {"run": 0}

    class FakeCoder:
        def __init__(self, *args, **kwargs):
            pass

        def run(self):
            calls["run"] += 1
            return lambda n: n * 2

    monkeypatch.setattr("jit_implementation.decorator.Coder", FakeCoder)

    @implement
    def double(n: int) -> int:
        """Double n."""
        ...

    assert double(3) == 6
    assert double(4) == 8
    assert calls["run"] == 1


def test_class_decorator_preserves_name_and_lazy_impl(monkeypatch):
    calls = {"run": 0}

    class FakeImpl:
        def __init__(self, value: int):
            self.value = value

    class FakeCoder:
        def __init__(self, *args, **kwargs):
            pass

        def run(self):
            calls["run"] += 1
            return FakeImpl

    monkeypatch.setattr("jit_implementation.decorator.Coder", FakeCoder)

    @implement
    class Widget:
        """Widget stub."""

    assert Widget.__name__ == "Widget"
    instance = Widget(7)
    assert instance.value == 7
    assert isinstance(instance, FakeImpl)
    assert calls["run"] == 1

    Widget(1)
    assert calls["run"] == 1
