import inspect
from typing import Any, Callable, TypeVar, overload

from jit_implementation.batch import BatchRegistry
from jit_implementation.config import Provider, Settings

T = TypeVar("T", bound=Callable[..., Any])


@overload
def implement_batch(batch_id: str, obj: T, /, *, provider: Provider | None = None) -> T: ...


@overload
def implement_batch(
    batch_id: str,
    *,
    provider: Provider | None = None,
) -> Callable[[T], T]: ...


def implement_batch(
    batch_id: str,
    obj: T | None = None,
    *,
    provider: Provider | None = None,
) -> T | Callable[[T], T]:
    """Register a stub for lazy batch implementation with other stubs sharing batch_id."""

    def decorator(wrapped: T) -> T:
        stub = inspect.unwrap(wrapped)
        stub._jit_batch_id = batch_id  # type: ignore[attr-defined]

        test_functions = getattr(wrapped, "_jit_test_functions", None)
        autonomous = getattr(wrapped, "_jit_autonomous", True)
        in_place = getattr(wrapped, "_jit_in_place", False)
        max_tries = getattr(wrapped, "_jit_max_tries", 5)
        wrapped_provider = getattr(wrapped, "_jit_provider", None)
        effective_provider = provider or wrapped_provider

        settings = Settings.from_env(max_tries=max_tries).with_provider(
            effective_provider
        )

        BatchRegistry.register(
            batch_id,
            stub,
            test_functions=test_functions,
            autonomous=autonomous,
            in_place=in_place,
            max_tries=max_tries,
            settings=settings,
        )
        return wrapped

    if obj is None:
        return decorator
    return decorator(obj)
