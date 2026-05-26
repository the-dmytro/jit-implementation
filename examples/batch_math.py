"""Example: lazy batch codegen with Cursor CLI.

Run from repo root (requires cursor-agent on PATH and auth):

    export JIT_IMPLEMENTATION_PROVIDER=cursor
    python examples/batch_math.py

The first call to either stub triggers one cursor-agent request for all
pending stubs in the batch.
"""

from jit_implementation import implement, implement_batch

BATCH = __name__


@implement_batch(BATCH, provider="cursor")
@implement(provider="cursor")
def fib(n: int) -> int:
    """Return nth Fibonacci number (fib(0)=0, fib(1)=1)."""
    ...


@implement_batch(BATCH, provider="cursor")
@implement(provider="cursor")
def factorial(n: int) -> int:
    """Return n! for n >= 0."""
    ...


if __name__ == "__main__":
    print("fib(10) =", fib(10))
    print("factorial(5) =", factorial(5))
