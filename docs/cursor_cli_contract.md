# Cursor CLI contract (local probe)

Probed on `cursor-agent` version `2026.05.16-0338208`.

## Invocation (phase 1)

```bash
cursor-agent \
  --workspace <repo_root> \
  -p \
  --output-format json \
  --trust \
  "<prompt>"
```

- Auth: `CURSOR_API_KEY` or `cursor-agent login`
- Optional: `--api-key <key>`
- Do **not** pass `--force` in phase 1 (read-only JSON output contract)

## Prompt contract

- Explicit: do not edit files; return only JSON
- Schema: `{"imports": ["..."], "code": "...", "chain_of_thought": ["..."]}`

## Parser expectations

Stdout may be raw JSON or a wrapper object; implementation tries:

1. `json.loads(stdout)` then unwrap common keys (`result`, `output`, `message`)
2. Fenced ` ```json ... ``` ` extraction
3. Pydantic validation via `GenerationOutput`

## Environment

| Variable | Default |
|----------|---------|
| `CURSOR_AGENT_BIN` | `cursor-agent` |
| `JIT_IMPLEMENTATION_WORKSPACE` | auto-detect from declaration file |
| `JIT_IMPLEMENTATION_CURSOR_TIMEOUT` | `300` (seconds) |
