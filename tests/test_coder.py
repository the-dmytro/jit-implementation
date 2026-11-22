import shutil

import pytest

from jit_implementation.coder import REVISION_TEMPLATE, Coder


class Widget:
    pass


def target(n: int) -> int:
    """Return n doubled."""


def make_coder(**kwargs) -> Coder:
    return Coder(target, **kwargs)


def test_model_defaults_to_class_constant(monkeypatch):
    monkeypatch.delenv(Coder.MODEL_ENV_VAR, raising=False)
    assert make_coder().model == Coder.MODEL


def test_model_from_env_var(monkeypatch):
    monkeypatch.setenv(Coder.MODEL_ENV_VAR, "env-model")
    assert make_coder().model == "env-model"


def test_model_param_overrides_env_var(monkeypatch):
    monkeypatch.setenv(Coder.MODEL_ENV_VAR, "env-model")
    assert make_coder(model="param-model").model == "param-model"


def test_reasoning_effort_defaults_to_class_constant(monkeypatch):
    monkeypatch.delenv(Coder.REASONING_EFFORT_ENV_VAR, raising=False)
    assert make_coder().reasoning_effort == Coder.REASONING_EFFORT


def test_reasoning_effort_from_env_var(monkeypatch):
    monkeypatch.setenv(Coder.REASONING_EFFORT_ENV_VAR, "minimal")
    assert make_coder().reasoning_effort == "minimal"


def test_reasoning_effort_param_overrides_env_var(monkeypatch):
    monkeypatch.setenv(Coder.REASONING_EFFORT_ENV_VAR, "minimal")
    assert make_coder(reasoning_effort="low").reasoning_effort == "low"


def test_reasoning_effort_empty_string_omits_parameter(monkeypatch):
    monkeypatch.delenv(Coder.REASONING_EFFORT_ENV_VAR, raising=False)
    assert make_coder(reasoning_effort="").reasoning_effort is None


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(Coder, "API_KEY", None)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        _ = make_coder().oai


def test_remove_duplicate_imports():
    code = "import os\nfrom sys import path\n\ndef f():\n    return os.name\n"
    assert (
        make_coder()._remove_duplicate_imports(code) == "def f():\n    return os.name"
    )


def test_compile_code_returns_object():
    coder = make_coder()
    obj = coder._compile_code("def target(n):\n    return n * 2\n")
    assert obj(21) == 42


def test_implementation_checksum_is_stable():
    assert (
        make_coder()._get_implementation_checksum()
        == make_coder()._get_implementation_checksum()
    )


def test_implementation_checksum_changes_with_tests():
    def case(f):
        return True, "ok"

    assert (
        make_coder()._get_implementation_checksum()
        != make_coder(test_functions=[case])._get_implementation_checksum()
    )


def test_should_reuse_code(tmp_path, monkeypatch):
    coder = make_coder()
    path = tmp_path / "target.py"
    monkeypatch.setattr(Coder, "code_path", property(lambda self: path))

    checksum = coder._get_implementation_checksum()
    assert coder._should_reuse_code(checksum) is False

    path.write_text(f"# Implementation Checksum: {checksum}\n")
    assert coder._should_reuse_code(checksum) is True
    assert coder._should_reuse_code("0" * 64) is False


def test_revision_template_renders_checksum():
    rendered = REVISION_TEMPLATE.render(
        version=1,
        timestamp="2026-01-01T00:00:00Z",
        tests_passed="PASSED",
        declaration_file="mod.py",
        implementation_checksum="abc123",
        imports="import os",
        chain_of_thought="step one",
        code="x = 1",
    )
    assert "Implementation Checksum: abc123" in rendered
    assert "x = 1" in rendered


@pytest.mark.skipif(shutil.which("ruff") is None, reason="ruff not installed")
def test_format_code_normalizes_source():
    formatted = make_coder()._format_code("def target(n):\n    return  n*2\n")
    assert formatted == "def target(n):\n    return n * 2\n"


def test_types_enum_preserves_type_names():
    types = {Widget}
    enum_cls = Coder._types_enum(types)
    member = enum_cls("Widget")
    assert member.value == "Widget"
    assert {t.__name__: t for t in types}[member] is Widget
