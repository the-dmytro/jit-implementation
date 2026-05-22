from pathlib import Path

from jit_implementation.backends.cursor_cli import create_cursor_backend
from jit_implementation.backends.generation import GenerationBackend
from jit_implementation.backends.openai_generation import OpenAIGenerationBackend
from jit_implementation.config import Settings
from jit_implementation.ide import IDE


def create_generation_backend(
    settings: Settings,
    *,
    ide: IDE,
    declaration_file: Path | None = None,
) -> GenerationBackend:
    if settings.provider == "cursor":
        if declaration_file is None:
            raise ValueError("declaration_file is required for cursor provider")
        return create_cursor_backend(settings, declaration_file=declaration_file)
    return OpenAIGenerationBackend(settings, ide=ide)
