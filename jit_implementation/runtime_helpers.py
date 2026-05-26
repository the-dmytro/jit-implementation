import hashlib
import inspect
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

from jinja2 import Template
from rich.console import Console

REVISION_TEMPLATE = Template("""\
# Version: {{ version }} - Generated on {{ timestamp }}

# Tests Passed: {{ tests_passed }}

# Declaration File: {{ declaration_file }}
# Implementation Checksum: {{ implementation_checksum }}

{% if chain_of_thought %}
# Chain of Thought:
# {{ chain_of_thought }}
{% endif %}

{% if imports %}
# Imports
{{ imports }}
{% endif %}

# Implementation
{{ code }}
""")


def get_implementation_checksum(
    obj: Any, test_functions: list[Callable[[Any], tuple[bool, str]]]
) -> str:
    declaration_source = inspect.getsource(obj)
    tests_str = "\n".join(inspect.getsource(func) for func in test_functions)
    return hashlib.sha256(f"{declaration_source}{tests_str}".encode()).hexdigest()


def code_path_for(
    obj: Any, *, cache_dir: Path, test_functions: list[Callable[[Any], tuple[bool, str]]]
) -> Path:
    declaration_file = Path(inspect.getfile(obj)).resolve()
    cache_key = hashlib.sha256(str(declaration_file).encode()).hexdigest()[:16]
    directory = cache_dir.resolve() / cache_key
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{obj.__name__}.py"


def should_reuse_code(path: Path, implementation_checksum: str) -> bool:
    if not path.exists():
        return False
    content = path.read_text()
    existing_hash = re.search(r"Implementation Checksum: (\w+)", content)
    return bool(existing_hash and existing_hash.group(1) == implementation_checksum)


def format_code(code: str, console: Console) -> str:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False
    ) as temp_file:
        temp_file.write(code)
        temp_file_path = temp_file.name

    try:
        console.print("Running Ruff to format code...")
        subprocess.run(
            ["ruff", "format", temp_file_path],
            check=True,
            capture_output=True,
        )
        with open(temp_file_path, "r") as fixed_file:
            return fixed_file.read()
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        console.print(f"[bold red]Ruff encountered an error:[/bold red] {stderr}")
        return code
    except FileNotFoundError:
        console.print("[yellow]Ruff is not installed; skipping format step.[/yellow]")
        return code
    finally:
        os.unlink(temp_file_path)


def remove_duplicate_imports(code: str) -> str:
    pattern = r"^\s*(import .*|from .* import .*)$"
    return re.sub(pattern, "", code, flags=re.MULTILINE).strip()


def compile_implementation(obj: Any, full_code: str) -> Any:
    compiled_code = compile(full_code, "<string>", "exec")
    namespace: dict[str, Any] = {}
    exec(compiled_code, namespace)
    return namespace[obj.__name__]


def run_tests(
    obj: Any,
    test_functions: list[Callable[[Any], tuple[bool, str]]],
    console: Console,
) -> tuple[bool, list[tuple[str, str | None]]]:
    failures: list[tuple[str, str | None]] = []
    for case in test_functions:
        try:
            passed, doc = case(obj)
        except Exception as exc:
            doc = getattr(case, "__name__", "test")
            failures.append((doc, f"{type(exc).__name__}: {exc}"))
            console.print(
                f"Test case `{doc}`: [red]FAILED[/red] ({type(exc).__name__}: {exc})"
            )
            continue

        console.print(
            f"Test case `{doc}`: "
            f"{'[green]PASSED[/green]' if passed else '[red]FAILED[/red]'}"
        )
        if not passed:
            failures.append((doc, "Assertion did not hold"))
    return (len(failures) == 0, failures)


def format_test_failures(failures: list[tuple[str, str | None]]) -> str:
    lines = ["One or more tests failed. Details:"]
    for description, detail in failures:
        lines.append(f"- {description}")
        if detail:
            lines.append(f"  {detail}")
    lines.append("Revise the implementation and submit an updated version.")
    return "\n".join(lines)
