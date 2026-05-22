class JITImplementationError(Exception):
    """Base error for jit-implementation."""


class MissingAPIKeyError(JITImplementationError):
    """Raised when OPENAI_API_KEY is not configured."""

    def __init__(self) -> None:
        super().__init__(
            "OPENAI_API_KEY environment variable is not set. "
            "Export your API key before using @implement."
        )
