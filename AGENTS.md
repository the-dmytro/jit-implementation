## Learned User Preferences

- Use the `cursor/` prefix for feature branches when starting agent-driven work in this repo.
- When implementing an attached plan, do not edit the plan file; execute against it as-is.
- If plan todos already exist, mark them in progress and complete them; do not recreate todos.
- Prefer phased delivery for major backends: ship single-stub generation first, then batch/multi-stub.
- Select codegen provider via both env (`JIT_IMPLEMENTATION_PROVIDER`) and `@implement(provider=...)` override.
- For substantial features, use relevant Cursor skills and subagents (e.g. cursor-cli, code review) during research and planning before coding.

## Learned Workspace Facts

- `jit-implementation` is a Python library: `@implement` lazy-generates function or class bodies on first call via LLM backends.
- `@implement_batch` generates multiple stubs in one generation call (batch / phase-2 path).
- Codegen backends include OpenAI (`GenerationBackend` / Responses path) and Cursor CLI (`cursor-agent` subprocess).
- Cursor CLI JSON contract and invocation details live in `docs/cursor_cli_contract.md`.
- Generated implementations are cached under `.jit_impl/` (override with `JIT_IMPLEMENTATION_CACHE_DIR`).
- Configuration is env-driven: `OPENAI_API_KEY`, `JIT_IMPLEMENTATION_MODEL`, `JIT_IMPLEMENTATION_PROVIDER`, `CURSOR_AGENT_BIN`, `CURSOR_API_KEY`.
- Tests use pytest under `tests/`; live API tests are integration-marked and gated.
