import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from pydantic import ValidationError

from jit_implementation.backends.generation import (
    BatchGenerationRequest,
    GenerationBackend,
    GenerationRequest,
    GenerationResult,
)
from jit_implementation.config import Settings
from jit_implementation.exceptions import CursorAgentError, CursorAgentNotFoundError
from jit_implementation.models import BatchGenerationOutput, GenerationOutput
from jit_implementation.workspace import resolve_workspace


class CursorCLIGenerationBackend(GenerationBackend):
    JSON_SCHEMA_INSTRUCTION = (
        'Return ONLY a single JSON object (no markdown fences) with keys: '
        '"imports" (list of strings), "code" (string, body without imports), '
        '"chain_of_thought" (list of strings). Do not edit any files.'
    )
    BATCH_JSON_SCHEMA_INSTRUCTION = (
        'Return ONLY a single JSON object (no markdown fences) with key '
        '"implementations" mapping each stub name to an object with keys: '
        '"imports" (list of strings), "code" (string), "chain_of_thought" (list). '
        "Do not edit any files."
    )

    def __init__(self, settings: Settings, *, workspace: Path) -> None:
        self._settings = settings
        self._workspace = workspace

    def generate(self, request: GenerationRequest) -> GenerationResult:
        binary = self._resolve_binary()
        prompt = self._build_prompt(request)
        command = [
            binary,
            "--workspace",
            str(self._workspace),
            "-p",
            "--output-format",
            "json",
            "--trust",
            prompt,
        ]

        env = os.environ.copy()
        if self._settings.cursor_api_key:
            env["CURSOR_API_KEY"] = self._settings.cursor_api_key

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self._settings.cursor_timeout_seconds,
                env=env,
                cwd=self._workspace,
            )
        except subprocess.TimeoutExpired as exc:
            raise CursorAgentError(
                f"cursor-agent timed out after {self._settings.cursor_timeout_seconds}s"
            ) from exc

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            raise CursorAgentError(
                f"cursor-agent exited with code {completed.returncode}"
                + (f": {stderr}" if stderr else "")
            )

        stdout = (completed.stdout or "").strip()
        if not stdout:
            raise CursorAgentError("cursor-agent returned empty stdout")

        try:
            payload = self._parse_stdout(stdout)
            output = GenerationOutput.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, CursorAgentError) as exc:
            raise CursorAgentError(
                f"Failed to parse cursor-agent JSON output: {exc}"
            ) from exc

        return GenerationResult(
            imports=output.imports,
            code=output.code,
            chain_of_thought=output.chain_of_thought,
        )

    def generate_batch(
        self, request: BatchGenerationRequest
    ) -> dict[str, GenerationResult]:
        binary = self._resolve_binary()
        prompt = self._build_batch_prompt(request)
        command = [
            binary,
            "--workspace",
            str(self._workspace),
            "-p",
            "--output-format",
            "json",
            "--trust",
            prompt,
        ]

        env = os.environ.copy()
        if self._settings.cursor_api_key:
            env["CURSOR_API_KEY"] = self._settings.cursor_api_key

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self._settings.cursor_batch_timeout_seconds,
                env=env,
                cwd=self._workspace,
            )
        except subprocess.TimeoutExpired as exc:
            raise CursorAgentError(
                "cursor-agent timed out after "
                f"{self._settings.cursor_batch_timeout_seconds}s"
            ) from exc

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            raise CursorAgentError(
                f"cursor-agent exited with code {completed.returncode}"
                + (f": {stderr}" if stderr else "")
            )

        stdout = (completed.stdout or "").strip()
        if not stdout:
            raise CursorAgentError("cursor-agent returned empty stdout")

        try:
            payload = self._parse_stdout(stdout)
            if "implementations" not in payload:
                payload = {"implementations": payload}
            batch_output = BatchGenerationOutput.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, CursorAgentError) as exc:
            raise CursorAgentError(
                f"Failed to parse cursor-agent batch JSON output: {exc}"
            ) from exc

        expected = {stub.name for stub in request.stubs}
        missing = expected - set(batch_output.implementations)
        if missing:
            raise CursorAgentError(
                f"Batch output missing implementations for: {', '.join(sorted(missing))}"
            )

        return {
            name: GenerationResult(
                imports=item.imports,
                code=item.code,
                chain_of_thought=item.chain_of_thought,
            )
            for name, item in batch_output.implementations.items()
        }

    def _resolve_binary(self) -> str:
        binary = self._settings.cursor_agent_bin
        path = shutil.which(binary)
        if not path:
            raise CursorAgentNotFoundError(binary)
        return path

    def _build_prompt(self, request: GenerationRequest) -> str:
        parts = [
            request.instructions,
            "",
            self.JSON_SCHEMA_INSTRUCTION,
            "",
            "Implement the following Python stub:",
            request.stub_source,
        ]
        if request.related_sources:
            parts.append("\nRelated project types:")
            for name, source in sorted(request.related_sources.items()):
                parts.append(f"\n--- {name} ---\n{source}")
        if request.failure_feedback:
            parts.append(f"\n{request.failure_feedback}")
        return "\n".join(parts)

    def _build_batch_prompt(self, request: BatchGenerationRequest) -> str:
        parts = [
            request.instructions,
            "",
            self.BATCH_JSON_SCHEMA_INSTRUCTION,
            "",
            "Implement ALL of the following Python stubs in one response.",
            "Use each stub's exact name as the JSON key under 'implementations'.",
        ]
        for stub in request.stubs:
            parts.append(f"\n--- Stub: {stub.name} ---\n{stub.stub_source}")
            if stub.failure_feedback:
                parts.append(f"Previous failure for {stub.name}:\n{stub.failure_feedback}")
        if request.related_sources:
            parts.append("\nRelated project types:")
            for name, source in sorted(request.related_sources.items()):
                parts.append(f"\n--- {name} ---\n{source}")
        if request.failure_feedback:
            parts.append("\nFailures from previous attempt:")
            for name, msg in sorted(request.failure_feedback.items()):
                parts.append(f"- {name}: {msg}")
        return "\n".join(parts)

    def _parse_stdout(self, stdout: str) -> dict:
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            data = None

        if isinstance(data, dict):
            unwrapped = self._unwrap_payload(data)
            if isinstance(unwrapped, dict) and "imports" in unwrapped and "code" in unwrapped:
                return unwrapped

        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stdout, re.DOTALL)
        if fenced:
            return json.loads(fenced.group(1))

        object_match = re.search(r"\{.*\}", stdout, re.DOTALL)
        if object_match:
            candidate = json.loads(object_match.group(0))
            if isinstance(candidate, dict):
                unwrapped = self._unwrap_payload(candidate)
                if isinstance(unwrapped, dict):
                    return unwrapped

        raise CursorAgentError("No JSON object with imports and code found in output")

    def _unwrap_payload(self, data: dict) -> dict:
        for key in ("result", "output", "message", "text", "content"):
            value = data.get(key)
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    fenced = re.search(
                        r"```(?:json)?\s*(\{.*?\})\s*```", value, re.DOTALL
                    )
                    if fenced:
                        return json.loads(fenced.group(1))
            if isinstance(value, dict):
                return value
        return data


def create_cursor_backend(
    settings: Settings, *, declaration_file: Path
) -> CursorCLIGenerationBackend:
    workspace = resolve_workspace(
        declaration_file,
        settings.workspace,
    )
    return CursorCLIGenerationBackend(settings, workspace=workspace)
