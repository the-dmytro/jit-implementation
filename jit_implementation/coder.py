import inspect
import os
import re
import subprocess
import sys
import tempfile
import hashlib
from typing import Any, Callable, List, Tuple
from pathlib import Path
import datetime as dt

import openai
from jinja2 import Template
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from jit_implementation.backends.responses import ResponsesBackend
from jit_implementation.config import DEFAULT_SETTINGS, Settings
from jit_implementation.exceptions import MissingAPIKeyError
from jit_implementation.ide import IDE
from jit_implementation.models import ReadSourceCode, Reasoning, SubmitVersion

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


class Coder:
    PROMPT: str = (
        "You are a senior developer tasked with implementing Python functions and classes.\n"
        "Follow these guidelines to produce high-quality, efficient, and maintainable code:\n"
        "\n"
        "1. Code Structure and Organization:\n"
        "   - Separate imports and code:\n"
        "     * Place all import statements in the 'imports' field.\n"
        "     * Put implementation code in the 'code' field, excluding import statements.\n"
        "   - Use meaningful names for variables, functions, and classes.\n"
        "\n"
        "2. Performance Optimization:\n"
        "   - Optimize for lowest time and space complexity.\n"
        "   - Use appropriate data structures (e.g., sets for membership testing, dictionaries for fast lookups).\n"
        "   - Employ efficient algorithms and avoid unnecessary computations.\n"
        "\n"
        "3. Code Quality and Readability:\n"
        "   - Follow PEP 8 style guide for Python code.\n"
        "   - Write self-documenting code with clear and concise variable and function names.\n"
        "   - Add comments for complex logic or non-obvious implementation details.\n"
        "   - Use type hints to improve code clarity and catch potential type-related errors.\n"
        "\n"
        "Remember: Write code that is not only functional but also maintainable and scalable."
    )

    def __init__(
        self,
        obj: Any,
        test_functions: List[Callable[[Any], Tuple[bool, str]]] | None = None,
        autonomous: bool = True,
        in_place: bool = False,
        max_tries: int | None = None,
        settings: Settings | None = None,
    ):
        self.obj = obj
        self.test_functions = test_functions or []
        self.autonomous = autonomous
        self.in_place = in_place
        self.settings = settings or DEFAULT_SETTINGS
        self.max_tries = max_tries if max_tries is not None else self.settings.max_tries

        self.console = Console()
        self.ide = IDE(self.obj)
        self._backend = ResponsesBackend(
            self._create_client(),
            model=self.settings.model,
            temperature=self.settings.temperature,
        )

    def _create_client(self) -> OpenAI:
        api_key = self.settings.api_key
        if not api_key:
            raise MissingAPIKeyError()
        return OpenAI(api_key=api_key)

    @property
    def code_path(self) -> Path:
        declaration_file = Path(inspect.getfile(self.obj)).resolve()
        cache_key = hashlib.sha256(str(declaration_file).encode()).hexdigest()[:16]
        directory = self.settings.cache_dir.resolve() / cache_key
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{self.obj.__name__}.py"

    def _format_code(self, code: str) -> str:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name

        try:
            self.console.print("Running Ruff to format code...")
            subprocess.run(
                ["ruff", "format", temp_file_path],
                check=True,
                capture_output=True,
            )
            with open(temp_file_path, "r") as fixed_file:
                return fixed_file.read()
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else str(e)
            self.console.print(
                f"[bold red]Ruff encountered an error:[/bold red] {stderr}"
            )
            return code
        except FileNotFoundError:
            self.console.print(
                "[yellow]Ruff is not installed; skipping format step.[/yellow]"
            )
            return code
        finally:
            os.unlink(temp_file_path)

    def _print_code(self, title: str, code: str) -> None:
        self.console.print(
            Panel(
                Syntax(code, "python", theme="monokai", line_numbers=True),
                title=title,
            )
        )

    def _print_llm_output(self, message: str) -> None:
        self.console.print(Text(message, style="bold cyan"))

    def _compile_code(self, code: str) -> Any:
        compiled_code = compile(code, "<string>", "exec")
        namespace: dict[str, Any] = {}
        exec(compiled_code, namespace)
        return namespace[self.obj.__name__]

    def _remove_duplicate_imports(self, code: str) -> str:
        pattern = r"^\s*(import .*|from .* import .*)$"
        return re.sub(pattern, "", code, flags=re.MULTILINE).strip()

    def _get_implementation_checksum(self) -> str:
        declaration_source = inspect.getsource(self.obj)
        tests_str = "\n".join(inspect.getsource(func) for func in self.test_functions)
        return hashlib.sha256(f"{declaration_source}{tests_str}".encode()).hexdigest()

    def _should_reuse_code(self, implementation_checksum: str) -> bool:
        if not self.code_path.exists():
            return False

        content = self.code_path.read_text()
        existing_hash = re.search(r"Implementation Checksum: (\w+)", content)
        return bool(existing_hash and existing_hash.group(1) == implementation_checksum)

    def _build_tools(self) -> list[Any]:
        tools = [
            openai.pydantic_function_tool(SubmitVersion),
            openai.pydantic_function_tool(Reasoning),
        ]
        if self.ide.unread_types:
            tools.append(openai.pydantic_function_tool(ReadSourceCode))
        return tools

    def _read_source_tool_hint(self) -> str:
        if not self.ide.unread_types:
            return ""
        names = ", ".join(sorted(t.__name__ for t in self.ide.unread_types))
        return f"\nAvailable types for ReadSourceCode: {names}"

    def _format_test_failures(
        self, failures: list[tuple[str, str | None]]
    ) -> str:
        lines = ["One or more tests failed. Details:"]
        for description, detail in failures:
            lines.append(f"- {description}")
            if detail:
                lines.append(f"  {detail}")
        lines.append("Revise the implementation and call SubmitVersion again.")
        return "\n".join(lines)

    def _run_tests(self, obj: Any) -> tuple[bool, list[tuple[str, str | None]]]:
        failures: list[tuple[str, str | None]] = []
        for case in self.test_functions:
            try:
                passed, doc = case(obj)
            except Exception as exc:
                passed = False
                doc = getattr(case, "__name__", "test")
                failures.append((doc, f"{type(exc).__name__}: {exc}"))
                self.console.print(
                    f"Test case `{doc}`: [red]FAILED[/red] ({type(exc).__name__}: {exc})"
                )
                continue

            self.console.print(
                f"Test case `{doc}`: "
                f"{'[green]PASSED[/green]' if passed else '[red]FAILED[/red]'}"
            )
            if not passed:
                failures.append((doc, "Assertion did not hold"))
        return (len(failures) == 0, failures)

    def run(self) -> Any:
        implementation_checksum = self._get_implementation_checksum()

        if self._should_reuse_code(implementation_checksum):
            return self._compile_code(self.code_path.read_text())

        self._print_code(
            "Callable to implement",
            self.ide.read_source(
                self.obj,
                postprocessor=lambda code: re.sub(
                    r"^(?:@[\s\S]*?(?:\n|$))*(?=\s*(?:def|class)\s)",
                    "",
                    code,
                    flags=re.MULTILINE,
                ),
            ),
        )

        user_content = (
            "Implement the following function or class in Python.\n"
            "Please remember to separate imports and code as per instructions.\n"
            f"Function or class to implement:\n{self.ide.read_source(self.obj)}"
            f"{self._read_source_tool_hint()}"
        )
        self._backend.begin(instructions=self.PROMPT, user_content=user_content)

        version = 0
        chain_of_thought: list[str] = []
        tries = 0

        while tries < self.max_tries:
            if not self.autonomous and tries > 0:
                if not self._prompt_continue():
                    self.console.print("[yellow]Operation cancelled by user.[/yellow]")
                    return None

            step = self._backend.complete_with_tools(self._build_tools())
            type_by_name = {t.__name__: t for t in self.ide.unread_types}

            for call in step.tool_calls:
                if call.name == "Reasoning" and isinstance(
                    call.parsed_arguments, Reasoning
                ):
                    chain_of_thought.extend(call.parsed_arguments.chain_of_thought)
                    self._print_llm_output("Chain of thought:")
                    self.console.print(
                        "\n".join(call.parsed_arguments.chain_of_thought)
                    )
                    self._backend.submit_tool_result(
                        call.call_id,
                        "Reasoning recorded. Continue with implementation.",
                    )

                elif call.name == "ReadSourceCode" and isinstance(
                    call.parsed_arguments, ReadSourceCode
                ):
                    type_name = call.parsed_arguments.type
                    self._print_llm_output(f"Reading source code of type: {type_name}")
                    if type_name not in type_by_name:
                        self._backend.submit_tool_result(
                            call.call_id,
                            f"Unknown type '{type_name}'. "
                            f"Available: {', '.join(type_by_name) or 'none'}.",
                        )
                        continue

                    source_code = self.ide.read_source(type_by_name[type_name])
                    self._print_code(f"Source of {type_name}", source_code or "")
                    self._backend.submit_tool_result(
                        call.call_id, source_code or ""
                    )

                elif call.name == "SubmitVersion" and isinstance(
                    call.parsed_arguments, SubmitVersion
                ):
                    version += 1
                    implementation = call.parsed_arguments
                    imports = implementation.imports
                    code = self._format_code(implementation.code)
                    code = self._remove_duplicate_imports(code)

                    self._print_code(
                        f"Implementation Version {version}",
                        "\n".join(imports) + "\n\n" + code,
                    )

                    full_code = "\n".join(imports) + "\n\n" + code
                    obj = self._compile_code(full_code)

                    passed, failures = self._run_tests(obj)
                    failed = not passed

                    code_path = (
                        self.code_path
                        if not failed
                        else self.code_path.with_suffix(f".v{version:02d}_failed.py")
                    )

                    code_path.write_text(
                        REVISION_TEMPLATE.render(
                            version=version,
                            timestamp=dt.datetime.now(dt.UTC).strftime(
                                "%Y-%m-%dT%H:%M:%SZ"
                            ),
                            tests_passed="PASSED" if not failed else "FAILED",
                            declaration_file=inspect.getfile(self.obj),
                            implementation_checksum=implementation_checksum,
                            imports="\n".join(imports),
                            chain_of_thought="# ".join(
                                "\n".join(chain_of_thought).splitlines(True)
                            ),
                            code=code,
                        )
                    )

                    if self.in_place and not failed:
                        file = inspect.getfile(self.obj)
                        source = Path(file).read_text()
                        source = source.replace(inspect.getsource(self.obj), code)
                        Path(file).write_text(source)

                        self.console.print(
                            "[green]Code updated in place. Restarting script...[/green]"
                        )
                        subprocess.Popen([sys.executable, *sys.argv])
                        sys.exit()

                    if not failed:
                        return obj

                    tries += 1
                    self._backend.submit_tool_result(
                        call.call_id, self._format_test_failures(failures)
                    )
                    if tries >= self.max_tries:
                        raise NotImplementedError(
                            f"Maximum number of tries ({self.max_tries}) reached "
                            "without passing tests."
                        )

        raise NotImplementedError(
            f"Maximum number of tries ({self.max_tries}) reached without implementation."
        )

    def _prompt_continue(self) -> bool:
        response = input("Continue to next iteration? (yes/no): ").strip().lower()
        return response in {"yes", "y", "continue"}
