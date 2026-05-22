import inspect
from functools import wraps
from typing import Any, Callable, List, Tuple, TypeVar, cast, overload

from jit_implementation.coder import Coder

T = TypeVar("T", bound=Callable[..., Any])


def _implement_callable(
    func: T,
    *,
    test_functions: List[Callable[[Any], Tuple[bool, str]]] | None,
    autonomous: bool,
    in_place: bool,
    max_tries: int,
) -> T:
    implemented: Any = None

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        nonlocal implemented
        if implemented is None:
            coder = Coder(
                func,
                test_functions,
                autonomous,
                in_place,
                max_tries,
            )
            implemented = coder.run()
        return implemented(*args, **kwargs)

    return cast(T, wrapper)


def _implement_class(
    stub: type,
    *,
    test_functions: List[Callable[[Any], Tuple[bool, str]]] | None,
    autonomous: bool,
    in_place: bool,
    max_tries: int,
) -> type:
    class JITMeta(type):
        __jit_stub__ = stub
        _implementation: type | None = None

        def __call__(mcls, *args: Any, **kwargs: Any) -> Any:
            if mcls._implementation is None:
                coder = Coder(
                    mcls.__jit_stub__,
                    test_functions,
                    autonomous,
                    in_place,
                    max_tries,
                )
                mcls._implementation = coder.run()
            return mcls._implementation(*args, **kwargs)

        def __instancecheck__(mcls, instance: Any) -> bool:
            if mcls._implementation is not None:
                return isinstance(instance, mcls._implementation)
            return type.__instancecheck__(mcls, instance)

    implemented_class = JITMeta(stub.__name__, (stub,), dict(stub.__dict__))
    implemented_class.__module__ = stub.__module__
    implemented_class.__qualname__ = stub.__qualname__
    if stub.__doc__:
        implemented_class.__doc__ = stub.__doc__
    return implemented_class


@overload
def implement(obj: T) -> T: ...


@overload
def implement(
    *,
    test_functions: List[Callable[[Any], Tuple[bool, str]]] | None = None,
    autonomous: bool = True,
    in_place: bool = False,
    max_tries: int = 5,
) -> Callable[[T], T]: ...


def implement(
    obj: T | None = None,
    *,
    test_functions: List[Callable[[Any], Tuple[bool, str]]] | None = None,
    autonomous: bool = True,
    in_place: bool = False,
    max_tries: int = 5,
) -> T | Callable[[T], T]:
    """Implements the decorated function or class just-in-time using AI-powered code generation."""

    def decorator(target: T) -> T:
        if inspect.isclass(target):
            return cast(T, _implement_class(
                target,
                test_functions=test_functions,
                autonomous=autonomous,
                in_place=in_place,
                max_tries=max_tries,
            ))
        return _implement_callable(
            target,
            test_functions=test_functions,
            autonomous=autonomous,
            in_place=in_place,
            max_tries=max_tries,
        )

    if obj is None:
        return decorator
    return decorator(obj)
