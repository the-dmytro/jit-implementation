import datetime as dt
import inspect
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from rich.console import Console

from jit_implementation.backends.factory import create_generation_backend
from jit_implementation.backends.generation import (
    BatchGenerationRequest,
    GenerationRequest,
    GenerationResult,
    StubSpec,
)
from jit_implementation.config import Provider, Settings
from jit_implementation.exceptions import InPlaceNotSupportedError
from jit_implementation.ide import IDE
from jit_implementation import runtime_helpers as rh


@dataclass
class BatchMember:
    obj: Any
    test_functions: list[Callable[[Any], tuple[bool, str]]]
    settings: Settings
    autonomous: bool
    in_place: bool
    max_tries: int
    implementation: Any | None = None


@dataclass
class BatchGroup:
    batch_id: str
    members: dict[str, BatchMember] = field(default_factory=dict)
    _resolved: bool = False


class BatchRegistry:
    _groups: dict[str, BatchGroup] = {}
    _lock = threading.Lock()

    @classmethod
    def register(
        cls,
        batch_id: str,
        obj: Any,
        *,
        test_functions: list[Callable[[Any], tuple[bool, str]]] | None,
        autonomous: bool,
        in_place: bool,
        max_tries: int,
        settings: Settings,
    ) -> None:
        with cls._lock:
            group = cls._groups.setdefault(batch_id, BatchGroup(batch_id=batch_id))
            group.members[obj.__name__] = BatchMember(
                obj=obj,
                test_functions=test_functions or [],
                settings=settings,
                autonomous=autonomous,
                in_place=in_place,
                max_tries=max_tries,
            )

    @classmethod
    def get_batch_id(cls, obj: Any) -> str | None:
        batch_id = getattr(obj, "_jit_batch_id", None)
        return batch_id

    @classmethod
    def get_member(cls, batch_id: str, name: str) -> BatchMember | None:
        with cls._lock:
            group = cls._groups.get(batch_id)
            if not group:
                return None
            return group.members.get(name)

    @classmethod
    def get_group(cls, batch_id: str) -> BatchGroup | None:
        with cls._lock:
            return cls._groups.get(batch_id)


class BatchCoordinator:
    @classmethod
    def ensure_implemented(cls, batch_id: str, obj: Any) -> Any:
        member = BatchRegistry.get_member(batch_id, obj.__name__)
        if member is None:
            raise KeyError(f"Stub {obj.__name__!r} is not registered in batch {batch_id!r}")

        if member.implementation is not None:
            return member.implementation

        with BatchRegistry._lock:
            group = BatchRegistry._groups.get(batch_id)
            if group is None:
                raise KeyError(f"Unknown batch {batch_id!r}")
            if group._resolved:
                if member.implementation is not None:
                    return member.implementation
                raise RuntimeError(
                    f"Batch {batch_id!r} resolved but {obj.__name__!r} has no implementation"
                )

            cls._resolve_batch(group)
            if all(m.implementation is not None for m in group.members.values()):
                group._resolved = True

        if member.implementation is None:
            raise RuntimeError(f"Failed to implement {obj.__name__!r} in batch {batch_id!r}")
        return member.implementation

    @classmethod
    def _resolve_batch(cls, group: BatchGroup) -> None:
        console = Console()
        pending = cls._pending_members(group, console)

        if not pending:
            for member in group.members.values():
                if member.implementation is None:
                    member.implementation = cls._load_from_cache(member, console)
            return

        if len(pending) == 1:
            cls._implement_single(pending[0], console)
            return

        settings = pending[0].settings
        if pending[0].in_place and settings.provider == "cursor":
            raise InPlaceNotSupportedError(settings.provider)

        declaration_file = Path(inspect.getfile(pending[0].obj)).resolve()
        backend = create_generation_backend(
            settings,
            ide=IDE(pending[0].obj),
            declaration_file=declaration_file,
        )

        tries = 0
        max_tries = pending[0].max_tries
        failure_feedback: dict[str, str] | None = None

        while tries < max_tries:
            if not pending[0].autonomous and tries > 0:
                response = input("Continue batch iteration? (yes/no): ").strip().lower()
                if response not in {"yes", "y", "continue"}:
                    console.print("[yellow]Batch cancelled by user.[/yellow]")
                    return

            request = cls._build_batch_request(pending, failure_feedback)
            results = backend.generate_batch(request)

            failures: dict[str, str] = {}
            for member in pending:
                result = results.get(member.obj.__name__)
                if result is None:
                    failures[member.obj.__name__] = "No implementation returned for this stub."
                    continue
                failed = cls._apply_result(member, result, console, version=tries + 1)
                if failed:
                    failures[member.obj.__name__] = failed

            if not failures:
                return

            tries += 1
            failure_feedback = failures
            if tries >= max_tries:
                names = ", ".join(failures)
                raise NotImplementedError(
                    f"Batch {group.batch_id!r} failed after {max_tries} tries: {names}"
                )

    @classmethod
    def _pending_members(
        cls, group: BatchGroup, console: Console
    ) -> list[BatchMember]:
        pending: list[BatchMember] = []
        for member in group.members.values():
            checksum = rh.get_implementation_checksum(member.obj, member.test_functions)
            path = rh.code_path_for(
                member.obj,
                cache_dir=member.settings.cache_dir,
                test_functions=member.test_functions,
            )
            if rh.should_reuse_code(path, checksum):
                member.implementation = rh.compile_implementation(
                    member.obj, path.read_text()
                )
            else:
                pending.append(member)
        return pending

    @classmethod
    def _load_from_cache(cls, member: BatchMember, console: Console) -> Any:
        path = rh.code_path_for(
            member.obj,
            cache_dir=member.settings.cache_dir,
            test_functions=member.test_functions,
        )
        return rh.compile_implementation(member.obj, path.read_text())

    @classmethod
    def _implement_single(cls, member: BatchMember, console: Console) -> None:
        from jit_implementation.coder import Coder

        coder = Coder(
            member.obj,
            member.test_functions,
            member.autonomous,
            member.in_place,
            member.max_tries,
            settings=member.settings,
            provider=member.settings.provider,
        )
        member.implementation = coder.run()

    @classmethod
    def _build_batch_request(
        cls,
        pending: list[BatchMember],
        failure_feedback: dict[str, str] | None,
    ) -> BatchGenerationRequest:
        from jit_implementation.coder import Coder

        related_sources: dict[str, str] = {}
        stubs: list[StubSpec] = []

        for member in pending:
            ide = IDE(member.obj)
            stub_source = ide.read_source(member.obj) or ""
            stubs.append(
                StubSpec(
                    name=member.obj.__name__,
                    obj=member.obj,
                    stub_source=stub_source,
                    test_functions=member.test_functions,
                    failure_feedback=(
                        failure_feedback.get(member.obj.__name__)
                        if failure_feedback
                        else None
                    ),
                )
            )
            cls._merge_related_sources(ide, related_sources)

        return BatchGenerationRequest(
            instructions=Coder.PROMPT,
            stubs=stubs,
            related_sources=related_sources,
            failure_feedback=failure_feedback,
        )

    @classmethod
    def _merge_related_sources(cls, ide: IDE, target: dict[str, str]) -> None:
        pending = list(ide.unread_types)
        while pending:
            typ = pending.pop()
            if typ.__name__ in target:
                continue
            source = ide.read_source(typ)
            if source:
                target[typ.__name__] = source
            pending.extend(t for t in ide.unread_types if t.__name__ not in target)

    @classmethod
    def _apply_result(
        cls,
        member: BatchMember,
        result: GenerationResult,
        console: Console,
        *,
        version: int,
    ) -> str | None:
        imports = result.imports
        code = rh.format_code(result.code, console)
        code = rh.remove_duplicate_imports(code)
        full_code = "\n".join(imports) + "\n\n" + code

        try:
            impl = rh.compile_implementation(member.obj, full_code)
        except Exception as exc:
            return f"Compile error: {type(exc).__name__}: {exc}"

        passed, failures = rh.run_tests(impl, member.test_functions, console)
        checksum = rh.get_implementation_checksum(member.obj, member.test_functions)
        path = (
            rh.code_path_for(
                member.obj,
                cache_dir=member.settings.cache_dir,
                test_functions=member.test_functions,
            )
            if passed
            else rh.code_path_for(
                member.obj,
                cache_dir=member.settings.cache_dir,
                test_functions=member.test_functions,
            ).with_suffix(f".v{version:02d}_failed.py")
        )

        path.write_text(
            rh.REVISION_TEMPLATE.render(
                version=version,
                timestamp=dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                tests_passed="PASSED" if passed else "FAILED",
                declaration_file=inspect.getfile(member.obj),
                implementation_checksum=checksum,
                imports="\n".join(imports),
                chain_of_thought="# ".join(
                    "\n".join(result.chain_of_thought).splitlines(True)
                ),
                code=code,
            )
        )

        if passed:
            member.implementation = impl
            return None
        return rh.format_test_failures(failures)
