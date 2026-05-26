# Changelog

## 0.4.0 — 2026-05-22

### Added

- **`@implement_batch(batch_id, ...)`** — lazy batch registration; first call to any member implements all pending stubs in the group.
- **`BatchCoordinator`** / `BatchRegistry` — thread-safe batch resolution, per-stub cache and tests.
- **`CursorCLIGenerationBackend.generate_batch()`** — one `cursor-agent` call with `implementations` JSON map ([docs/cursor_cli_contract.md](docs/cursor_cli_contract.md)).
- **`OpenAIGenerationBackend.generate_batch()`** — sequential `generate()` per stub (same coordinator API).
- **`jit_implementation.runtime_helpers`** — shared cache, format, compile, and test helpers for `Coder` and batch paths.
- **`JIT_IMPLEMENTATION_CURSOR_BATCH_TIMEOUT`** (default 600s).
- Gated integration tests: `tests/test_integration_cursor.py` (`pytest -m integration`).
- Example: [examples/batch_math.py](examples/batch_math.py).

### Changed

- `Coder` delegates cache/compile/test steps to `runtime_helpers`.
- Export `implement_batch` from `jit_implementation`.

## 0.3.0 — 2026-05-22

### Added

- **Cursor CLI provider** (`JIT_IMPLEMENTATION_PROVIDER=cursor` or `@implement(provider="cursor")`).
- `CursorCLIGenerationBackend`: one `cursor-agent -p --output-format json` call per attempt.
- `GenerationBackend` protocol unifying OpenAI and Cursor codegen paths.
- `OpenAIGenerationBackend` (extracted tool-loop from `Coder`).
- Provider factory, workspace auto-detection, and Cursor-specific errors.
- Docs: [docs/cursor_cli_contract.md](docs/cursor_cli_contract.md).

### Changed

- `Coder.run()` uses a single retry loop for all providers (cache → generate → test → retry).
- Related type sources are preloaded for the Cursor provider (no `ReadSourceCode` round-trips).

### Notes

- `in_place=True` is rejected when `provider=cursor`.
- Batch multi-stub generation ships in **0.4.0** (see above).

## 0.2.0 — 2026-05-22

### Breaking

- Requires `openai` Python SDK **2.37+** and the **Responses API** (no Chat Completions backend).
- Default model is now configurable via `JIT_IMPLEMENTATION_MODEL` (default: `gpt-4.1`).
- `ruff` is no longer a runtime dependency; install it separately or via `pip install jit-implementation[format]` if you use formatting.

### Added

- `jit_implementation.config.Settings` and `DEFAULT_SETTINGS` for environment-based configuration.
- `MissingAPIKeyError` instead of calling `quit()` when `OPENAI_API_KEY` is missing.
- `jit_implementation.backends.ResponsesBackend` with an `LLMBackend` protocol.
- Cache paths keyed by absolute declaration file path (stable across working-directory changes).
- Richer test-failure feedback sent back to the model on retry.
- Unit tests with `pytest`.

### Changed

- `@implement` on classes uses a metaclass so the decorated name is preserved and implementation is lazy on first instantiation.
- `ReadSourceCode` tool uses a string `type` field with available names listed in the prompt.

### Migration

```bash
pip install --upgrade "jit-implementation>=0.2.0" "openai>=2.37"
export OPENAI_API_KEY=...
export JIT_IMPLEMENTATION_MODEL=gpt-4.1   # or your preferred codegen model
```

## 0.1.5

- Initial public release using Chat Completions `beta.chat.completions.parse`.
