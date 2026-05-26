import pytest

from jit_implementation.coder import Coder
from jit_implementation.config import Settings
from jit_implementation.exceptions import InPlaceNotSupportedError


def test_in_place_cursor_raises():
    def sample():
        """stub"""

    settings = Settings(
        provider="cursor",
        api_key=None,
        model="x",
        temperature=0.0,
        max_tries=1,
        cache_dir=".jit_impl",
        cursor_agent_bin="cursor-agent",
        cursor_api_key=None,
        workspace=None,
        cursor_timeout_seconds=30,
        cursor_batch_timeout_seconds=600,
    )
    with pytest.raises(InPlaceNotSupportedError):
        Coder(sample, in_place=True, settings=settings)
