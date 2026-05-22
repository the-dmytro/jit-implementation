from jit_implementation.workspace import resolve_workspace


def test_resolve_workspace_finds_git(tmp_path):
    repo = tmp_path / "proj"
    repo.mkdir()
    (repo / ".git").mkdir()
    nested = repo / "pkg" / "mod.py"
    nested.parent.mkdir(parents=True)
    nested.touch()
    assert resolve_workspace(nested) == repo.resolve()


def test_resolve_workspace_override(tmp_path):
    override = tmp_path / "custom"
    override.mkdir()
    start = tmp_path / "elsewhere" / "file.py"
    start.parent.mkdir(parents=True)
    start.touch()
    assert resolve_workspace(start, override) == override.resolve()
