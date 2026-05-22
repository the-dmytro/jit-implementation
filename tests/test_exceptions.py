import pytest

from jit_implementation.coder import Coder
from jit_implementation.config import Settings
from jit_implementation.exceptions import MissingAPIKeyError


def test_missing_api_key_raises():
    def sample():
        """Doc."""

    with pytest.raises(MissingAPIKeyError):
        Coder(
            sample,
            settings=Settings(
                provider="openai",
                api_key=None,
                model="gpt-test",
                temperature=0.0,
                max_tries=1,
                cache_dir=".jit_impl",
                cursor_agent_bin="cursor-agent",
                cursor_api_key=None,
                workspace=None,
                cursor_timeout_seconds=300,
            ),
        )
