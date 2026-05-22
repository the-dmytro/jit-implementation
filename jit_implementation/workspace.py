from pathlib import Path


def resolve_workspace(start: Path, override: Path | None = None) -> Path:
    if override is not None:
        return override.resolve()

    path = start.resolve()
    candidates = [path, *path.parents]
    for candidate in candidates:
        if (candidate / ".git").exists() or (candidate / "pyproject.toml").exists():
            return candidate
    return path.parent
