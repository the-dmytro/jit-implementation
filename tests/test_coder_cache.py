import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

from jit_implementation.coder import Coder
from jit_implementation.config import Settings
from jit_implementation import runtime_helpers as rh


def test_code_path_is_stable_across_cwd(tmp_path, monkeypatch):
    declaration = tmp_path / "pkg" / "module.py"
    declaration.parent.mkdir(parents=True)
    declaration.write_text('def sample():\n    """Doc."""\n    ...\n')

    settings = Settings(
        provider="openai",
        api_key="x",
        model="gpt-test",
        temperature=0.0,
        max_tries=5,
        cache_dir=tmp_path / "cache",
        cursor_agent_bin="cursor-agent",
        cursor_api_key=None,
        workspace=None,
        cursor_timeout_seconds=300,
        cursor_batch_timeout_seconds=600,
    )

    def sample():
        """Doc."""

    with patch.object(Coder, "__init__", lambda self, obj, *a, **k: None):
        coder = Coder.__new__(Coder)
        coder.obj = sample
        coder.test_functions = []
        coder.settings = settings

        with patch("jit_implementation.coder.inspect.getfile", return_value=str(declaration)):
            path_a = coder.code_path

        other = tmp_path / "other"
        other.mkdir(exist_ok=True)
        monkeypatch.chdir(other)

        with patch("jit_implementation.coder.inspect.getfile", return_value=str(declaration)):
            path_b = coder.code_path

    assert path_a == path_b
    expected_parent = (tmp_path / "cache").resolve() / hashlib.sha256(
        str(declaration.resolve()).encode()
    ).hexdigest()[:16]
    assert path_a.parent == expected_parent


def test_checksum_changes_when_declaration_changes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = Settings(
        provider="openai",
        api_key="x",
        model="gpt-test",
        temperature=0.0,
        max_tries=5,
        cache_dir=tmp_path / "cache",
        cursor_agent_bin="cursor-agent",
        cursor_api_key=None,
        workspace=None,
        cursor_timeout_seconds=300,
        cursor_batch_timeout_seconds=600,
    )

    source = tmp_path / "sample.py"
    source.write_text('def sample():\n    """One."""\n    ...\n')

    def make_checksum(source_text: str) -> str:
        def sample():
            """placeholder"""

        with patch(
            "jit_implementation.coder.inspect.getsource", return_value=source_text
        ), patch(
            "jit_implementation.coder.inspect.getfile", return_value=str(source)
        ), patch(
            "jit_implementation.coder.create_generation_backend",
            return_value=MagicMock(),
        ):
            coder = Coder(sample, settings=settings)
            return rh.get_implementation_checksum(coder.obj, coder.test_functions)

    checksum_a = make_checksum('def sample():\n    """One."""\n    ...\n')
    checksum_b = make_checksum('def sample():\n    """Two."""\n    ...\n')

    assert checksum_a != checksum_b
