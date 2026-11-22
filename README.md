# JIT Implementation: A Python Library That Implements Your Code at Runtime

## You've heard of Just-in-Time Compilation. Now, get ready for Just-in-Time Implementation!

Tired of writing code? Let your programs write themselves with JIT Implementation!

### Quick Start

```python
from jit_implementation import implement


@implement
class Snake:
    """Snake game in pygame. Initializing launches the game."""


if __name__ == "__main__":
    Snake()

# You've just created a fully functional Snake game in just a few lines of code!
```

Yes, it actually works! Who needs hundreds of lines of code when you have JIT Implementation?

### What is JIT Implementation?

JIT Implementation is a groundbreaking Python library that generates your functions and classes on the fly using Large Language Models (LLMs). Simply decorate your function or class with `@implement`, and watch the magic unfold!

### Key Features

-   **Lazy Implementation**: Code is dynamically created when needed.
-   **Lighter Builds**: Enjoy feather-light builds since the code isn't even there until you need it!
-   **Context-Aware**: Analyzes your codebase to understand custom types and project structure.
-   **Test-Driven Development**: Provide test cases, and JIT Implementation ensures they pass.
-   **Smart Caching**: Stores generated implementations for reuse.

### Installation

Requires Python 3.12 or newer.

```bash
pip install jit-implementation
```

To run the `snake.py` example, also install the optional pygame dependency:

```bash
pip install "jit-implementation[examples]"
```

### Configuration

Set your OpenAI API key via the `OPENAI_API_KEY` environment variable (or assign `Coder.API_KEY` in code). The model defaults to `gpt-6-sol` and can be overridden with the `JIT_IMPLEMENTATION_MODEL` environment variable or the `model=` parameter of `@implement`:

```python
@implement(model="gpt-6-luna")
def fib(n: int) -> int: ...
```

The reasoning effort defaults to `none` (compatible with the default model) and can be overridden with the `JIT_IMPLEMENTATION_REASONING_EFFORT` environment variable or the `reasoning_effort=` parameter. Choose an effort supported by your model (e.g. `minimal` for `gpt-5`), or pass an empty string to omit the parameter:

```python
@implement(model="gpt-5", reasoning_effort="minimal")
def fib(n: int) -> int: ...
```

### Decorator Options

`@implement` can be used bare or with keyword arguments:

| Option | Default | Description |
| --- | --- | --- |
| `test_functions` | `None` | List of callables that take the implementation and return `(passed: bool, description: str)`. |
| `autonomous` | `True` | When `False`, asks for confirmation before each new iteration. |
| `in_place` | `False` | Rewrite the declaration in your source file with the generated code. |
| `max_tries` | `5` | Maximum generation attempts before raising `NotImplementedError`. |
| `model` | `None` | OpenAI model; overrides `JIT_IMPLEMENTATION_MODEL`. |
| `reasoning_effort` | `None` | Reasoning effort; overrides `JIT_IMPLEMENTATION_REASONING_EFFORT`. |

### Advanced Usage

```python
from jit_implementation import implement


@implement(
    test_functions=[
        lambda f: (f(100) == [2, 2, 5, 5], "Prime factors of 100"),
    ]
)
def prime_factors(n: int) -> list[int]:
    """Return the prime factors of n"""


assert prime_factors(100) == [2, 2, 5, 5]
assert prime_factors(69420) == [2, 2, 3, 5, 13, 89]
```

### In-Place Code Generation

For the brave souls who trust AI completely, JIT Implementation offers an `in_place=True` option that rewrites the source code in the file where the function was declared:

```python
@implement(in_place=True)
def fib(n: int) -> int:
    """Return the nth Fibonacci number"""


# After running the code, your source file will be updated with the implementation!
```

**Warning**: Use `in_place=True` with extreme caution. It will modify your source code!

### How It Works

1. **Define**: Provide a function or class signature with a docstring.
2. **Generate**: JIT Implementation uses an LLM to create the implementation.
3. **Validate**: Tests are run (if provided) and iterations are made if necessary.
4. **Cache**: Generated code is stored in the `.jit_impl/` directory, mirroring your project layout. It is reused until the declaration or its tests change (tracked via a SHA-256 checksum).

Generated code is formatted with Ruff before it is saved.

### Examples

Runnable examples live in the [`examples/`](examples) directory:

-   `fib.py` – Fibonacci numbers
-   `primes.py` – prime factorization validated by tests
-   `sliding_window.py` – sliding windows over a list
-   `snake.py` – a complete Snake game (requires the `examples` extra)

### Development

```bash
poetry install --with dev
poetry run ruff check .
poetry run ruff format --check .
poetry run pytest
```

CI runs linting, format checks and tests on Python 3.12–3.15.

### Warning

While powerful, use JIT Implementation responsibly:

-   Always review generated code before production use.
-   Be aware of potential security vulnerabilities.
-   Don't let it hinder your learning and problem-solving skills.

## Disclaimer

This project is for educational and experimental purposes. Do not rely on it for critical systems without thorough review.

## Support the Project

If you find JIT Implementation helpful or amusing, consider buying me a coffee!

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/the_dmytro)

---

**Note**: JIT Implementation was created as a joke. While it demonstrates interesting possibilities, it's not intended for serious development use.

_"The best code is the code you didn't have to write." - Anonymous JIT Implementation User_
