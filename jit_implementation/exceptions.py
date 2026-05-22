class JITImplementationError(Exception):
    """Base error for jit-implementation."""


class MissingAPIKeyError(JITImplementationError):
    """Raised when OPENAI_API_KEY is not configured."""

    def __init__(self) -> None:
        super().__init__(
            "OPENAI_API_KEY environment variable is not set. "
            "Export your API key before using @implement with provider='openai'."
        )


class InPlaceNotSupportedError(JITImplementationError):
    """Raised when in_place=True is used with an unsupported provider."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            f"in_place=True is not supported with provider='{provider}'. "
            "Use provider='openai' or disable in_place."
        )


class CursorAgentNotFoundError(JITImplementationError):
    """Raised when the cursor-agent binary is not on PATH."""

    def __init__(self, binary: str) -> None:
        super().__init__(
            f"Cursor CLI binary '{binary}' was not found on PATH. "
            "Install Cursor CLI and ensure cursor-agent is available."
        )


class CursorAgentError(JITImplementationError):
    """Raised when cursor-agent fails, times out, or returns unparseable output."""
