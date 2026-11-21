from collections.abc import Callable
from functools import wraps
from typing import Any, cast, overload

from jit_implementation.coder import Coder


@overload
def implement[T: Callable](
    obj: T,
) -> T: ...


@overload
def implement[T: Callable](
    *,
    test_functions: list[Callable[[Any], tuple[bool, str]]] | None = None,
    autonomous: bool = True,
    in_place: bool = False,
    max_tries: int = 5,
    model: str | None = None,
) -> Callable[[T], T]: ...


def implement[T: Callable](
    obj: T | None = None,
    *,
    test_functions: list[Callable[[Any], tuple[bool, str]]] | None = None,
    autonomous: bool = True,
    in_place: bool = False,
    max_tries: int = 5,
    model: str | None = None,
) -> T | Callable[[T], T]:
    """Implements the decorated function or class just-in-time using AI-powered code generation.

    This decorator uses a Large Language Model to generate an implementation based on the function
    signature, docstring, and optional test cases. It can be used to quickly prototype functions
    or create placeholder implementations that pass specified tests.

    Args:
        test_functions (list[Callable[[Any], tuple[bool, str]]], optional): A list of test functions
            to validate the implementation. Each function should take the implemented object as an
            argument and return a tuple of (bool, str), where the bool indicates if the test passed
            and the str is a description of the test. Defaults to None.
        autonomous (bool, optional): If True, the implementation will be generated without user
            interaction. If False, the user may be prompted for input during the implementation
            process. Defaults to True.
        in_place (bool, optional): If True, the source file of the decorated object will be modified
            to include the generated implementation. If False, the implementation will be stored
            separately. Defaults to False.
        max_tries (int, optional): The maximum number of attempts to generate a valid implementation
            that passes all tests. Defaults to 5.
        model (str, optional): The OpenAI model used for code generation. Overrides the
            JIT_IMPLEMENTATION_MODEL environment variable and the Coder.MODEL default.
            Defaults to None.

    Returns:
        Callable: The decorated function or class with the implemented functionality.

    Notes:
        - The quality and correctness of the implementation depend on the clarity of the
          function signature, docstring, and provided test cases.
        - Use this decorator responsibly and always review and test the generated code
          before using it in production environments.
    """

    def decorator(func: T) -> T:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            coder = Coder(func, test_functions, autonomous, in_place, max_tries, model)
            implemented_func = coder.run()
            return implemented_func(*args, **kwargs)

        return cast(T, wrapper)

    if obj is None:
        return decorator
    return decorator(obj)
