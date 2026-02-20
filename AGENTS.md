# AGENTS

This document defines the project rules for coding agents working in this repository.

## Project goals
- **Spec-first design**: The TOML spec is the single source of truth (SSOT).
- **Determinism**: Same spec + same version + same seed => same results.
- **Pyaedt backend**: Delegate modeling/simulation to Pyaedt.
- **Dataset generation**: Produce datasets via parameter sweeps/sampling.

## Working principles
- Any spec change must be reflected in docs (README or spec docs).
- Random/sampling logic must always accept an explicit `seed`.
- Document defaults; do not hide implicit values.
- Keep Pyaedt-dependent code isolated and replaceable.
- Do not add features that assume a UI/GUI (headless AEDT, GUI off).
- Keep execution configuration (machines, runners) in Python code, not in TOML.
- Prefer thorough type hints across the codebase.
- Do not use `Any` unless there is a hard external boundary that cannot be typed precisely; document the reason when `Any` is unavoidable.
- If a value is expected to be a concrete runtime type, prefer explicit runtime checks and `assert` to fail fast instead of passing loosely typed values through.
- Do not replace `Any` with broad `object` just to satisfy a type checker; use concrete library types whenever available (for example, `Hfss`, `Modeler3D` from `ansys.aedt.core`).
- Use a project-root virtual environment at `.venv` for local installs and commands.
- Agents can use `.venv` as the Python interpreter when running or linting code in this repo.
- Always prefer commands via `.venv` binaries (for example, `.venv/bin/python`, `.venv/bin/pytest`).
- Always check and resolve Pylance diagnostics (`reportArgumentType`, `reportCallIssue`, `reportGeneralTypeIssues`, etc.) before considering work complete.
- Recommended: download Pyaedt docs to `ref/pyaedt-doc-v0.24.1` for local reference.
- Agents can consult `ref/pyaedt-doc-v0.24.1` when implementing or modifying Pyaedt-related code.
- In long sessions, restate key assumptions and re-check AGENTS/README for drift before major changes.
- Keep the TOML-to-code mapping one-to-one; avoid generating multiple code paths per spec.
- Ensure (TOML + seed) deterministically maps to final parameters; treat this as a testable contract.
- Preflight validation must report what is supported vs. unsupported before design generation.

## Spec rules
- Use standard TOML only (no custom DSL).
- Consider a spec version bump when adding new parameters.
- Keep spec `path` as a stable dot notation.
- Keep a simple backward-compatibility policy documented in spec docs.
- Keep `run/type1.toml` as the primary runnable example spec, and include rich explanatory comments for each section/parameter.

## Tests/execution
- Prefer pure-Python tests for the spec parser/validator.
- Separate integration tests that require Pyaedt.
- Do not include large dataset generation in default test runs.
- Determinism tests are required; Pyaedt integration tests are optional.
- Run commands from the `run/` directory when executing scripts/tests to avoid polluting the repo root with generated artifacts.
- Prefer output paths under `run/` for manifests, AEDT files, logs, and temporary execution artifacts.

## File layout (planned)
- `peetsfea/`: library code
- `peetsfea/spec/`: schema/validation/normalization
- `peetsfea/backend/`: Pyaedt adapters
- `examples/`: TOML examples
- `docs/`: spec/design docs

## Discord notifications (MCP)
- Send a Discord message via `mcp__discord__discord_send` when work is finished.
- Skip Discord notifications when total task time is under 5 minutes.
- Do not estimate duration; compute it in shell seconds.
  - At start: `start_ts=$(date +%s)`
  - At end: `end_ts=$(date +%s); elapsed=$((end_ts-start_ts))`
  - Send Discord notification only when `elapsed >= 300`.
- On success, start with `Codex 완료`, then add a 1-2 line summary and next action (if any).
- On failure/interruption, start with `Codex 실패`, then add a short cause summary.

## Discord MCP setup (`~/.codex`)
- Ensure `~/.codex/config.toml` has an enabled Discord MCP server:
  - `[mcp_servers.discord]`
  - `enabled = true`
  - `url = "http://127.0.0.1:17870/mcp"`
- Keep allowed tools configured for Discord usage:
  - `discord_send`, `discord_list_servers`, `discord_get_server_info`
  - `discord_create_text_channel`, `discord_delete_channel`
- Optional timeout tuning:
  - `startup_timeout_sec = 20`
  - `tool_timeout_sec = 60`
- Resolve IDs before first use:
  - `mcp__discord__discord_list_servers` -> get `guildId`
  - `mcp__discord__discord_get_server_info` -> pick `channelId`

## Discord test
- Send a smoke-test message with your name using `mcp__discord__discord_send`.
