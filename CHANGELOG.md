# Changelog

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
