> Global code commandments live in [CODE_COMMANDMENTS.md](CODE_COMMANDMENTS.md) and are mandatory for the entire repository.
> Commandment 1 is active now: every real failure must raise and stop execution by default.
> Commandment 2 is active now: if a PyAEDT call returns `False`, raise immediately with context; never log-and-continue.
> Commandment 3 is active now for all `src/`: repository runtime state must not be nullable.
> Commandment 4 is active now for `src/`: bind values only after asserted validation.
> Commandment 5 is active now for `src/`: attribute and mapping fallbacks are forbidden.
> Fallbacks are forbidden: do not add fallback code paths, degraded substitutes, silent retries, or "try alternative behavior and continue" logic unless the user explicitly requests that behavior for the current task.
> Never launch AEDT in GUI mode unless the user explicitly asks for GUI validation.
# AGENTS

This document defines the project rules for coding agents working in this repository.

## Project goals
- **Spec-first design**: The TOML spec is the single source of truth (SSOT).
- **Determinism**: Same spec + same version + same seed => same results.
- **Pyaedt backend**: Delegate modeling/simulation to Pyaedt.
- **Dataset generation**: Produce datasets via parameter sweeps/sampling.

## Working principles
- Follow the repository-wide commandments in `CODE_COMMANDMENTS.md`; this document supplements them and must not weaken them.
- Do not implement fallback behavior by default. If the intended path fails or is unsupported, raise immediately with actionable context instead of switching to an alternate path.
- In `src/`, do not introduce `Optional[...]`, `| None`, `NotRequired[...]`, `if value is None`, or `if value is not None` for repository runtime state, including parser and boundary code.
- In `src/`, validate dynamic values before binding them: `assert hasattr(...)`, read, then `assert isinstance(...)` or assert an equivalent invariant.
- In `src/`, do not use `getattr(..., default)`, `mapping.get(...)`, or similar fallback-return APIs for required state, including parser and boundary code.
- If state must survive across steps, prefer a canonical module-level registry/dictionary and require `assert key in registry` before reads.
- Any spec change must be reflected in docs (README or spec docs).
- Random/sampling logic must always accept an explicit `seed`.
- Document defaults; do not hide implicit values.
- Keep Pyaedt-dependent code isolated and replaceable.
- Do not add features that assume a UI/GUI (headless AEDT, GUI off).
- Keep execution configuration (machines, runners) in Python code, not in TOML.
- When later logic needs the position/coordinates of an already created object, do not reverse-calculate them from downstream geometry; store the canonical coordinates in an accessible location at creation time and read from that source thereafter.
- If existing code currently depends on post-hoc coordinate reverse-calculation for created objects, refactor it to persist and reuse the creation-time coordinates instead of preserving the reverse-calculation path.
- Prefer thorough type hints across the codebase.
- Do not use `Any` unless there is a hard external boundary that cannot be typed precisely; document the reason when `Any` is unavoidable.
- If a value is expected to be a concrete runtime type, prefer explicit runtime checks and `assert` to fail fast instead of passing loosely typed values through.
- Do not replace `Any` with broad `object` just to satisfy a type checker; use concrete library types whenever available (for example, `Hfss`, `Modeler3D` from `ansys.aedt.core`).
- Use a project-root virtual environment at `.venv` for local installs and commands.
- Agents can use `.venv` as the Python interpreter when running or linting code in this repo.
- Always prefer commands via `.venv` binaries (for example, `.venv/bin/python`, `.venv/bin/pytest`).
- Do not use `python -O`; optimized mode disables required assertions and is unsupported in this repository.
- Always check and resolve Pylance diagnostics (`reportArgumentType`, `reportCallIssue`, `reportGeneralTypeIssues`, etc.) before considering work complete.
- Recommended: download Pyaedt docs to `ref/pyaedt-doc-v0.24.1` for local reference.
- Agents can consult `ref/pyaedt-doc-v0.24.1` when implementing or modifying Pyaedt-related code.
- In long sessions, restate key assumptions and re-check AGENTS/README for drift before major changes.
- Keep the TOML-to-code mapping one-to-one; avoid generating multiple code paths per spec.
- Ensure (TOML + seed) deterministically maps to final parameters; treat this as a testable contract.
- Preflight validation must report what is supported vs. unsupported before design generation.

## Sampling and replay rules
- Every independent sampled degree of freedom must have exactly one canonical owner.
- New sampled fields must be registered once in a shared sampling registry; do not sample the same meaning from multiple paths.
- Alias/derived paths must not own sampling; they may only reference a canonical owner.
- Do not implement candidate generation or candidate selection outside the shared sampling API.
- Values that are normalized away and do not affect the final design must stay fixed (`count=1` or equivalent fixed value).
- `dataset.toml` is the sampled-coordinate ledger for effective sampled degrees of freedom only.
- `repro.toml` must remain an exact replay artifact for the realized design.
- If a sampled field is added or changed, update docs, replay tests, dataset coverage tests, and dimension-audit tests together.
- Do not hardcode an example spec dimension count as a permanent contract; derive it from the registry/audit result.

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
- Use `entry/sample.py` for windowed batch TOML generation, `entry/build.py` for the derived batch-series AEDT generation, and `entry/sample_build.py` only for the GUI debug flow.
- Do not run those entry scripts directly from arbitrary cwd without the matching cleanup step.
- Default execution must stay headless. Do not launch GUI-visible AEDT or `entry/sample_build.py` during routine implementation, refactoring, or automated validation.
- GUI-mode AEDT verification is opt-in only and must not be run unless the user explicitly requests it for the current task.
- Even when GUI verification is requested, treat it as a validation step only; the implementation itself must remain headless-compatible.
- GUI validation is considered valid only when started through `.vscode/launch.json` using `Run entry/sample_build.py from run/`.
- Ad-hoc GUI launches such as direct `python ../entry/sample_build.py`, direct manifest-entry execution, or direct `build_aedt_from_manifest_entry_with_options()` calls are not valid GUI validation evidence.
- Agents must not infer product/runtime bugs from GUI behavior observed through non-regular launch paths.
- Required sequence:
  - For TOML generation, run the `run-sample-debug` task; it installs editable deps, clears `run/toml/`, and runs `../.venv/bin/python ../entry/sample.py` from `run/` in one task.
  - For AEDT generation from existing batch manifests, run the `prepare-build-debug` task first (this clears `run/aedt/`), then run `../.venv/bin/python ../entry/build.py` from `run/`.
  - For GUI validation, launch `Run entry/sample_build.py from run/`; its `preLaunchTask` is `prepare-build-debug`, so it clears `run/aedt/` before starting.
- Build/run failures must be fail-fast by default:
  - Do not silently continue to the next design after a failed build.
  - Use `stop_on_error=True` / `raise_on_error=True` for execution paths unless the user explicitly requests best-effort continuation.
- Rationale: stale `run/aedt/*.aedt.lock` files can cause HFSS startup/open failures.

## File layout (planned)
- `peetsfea/`: library code
- `peetsfea/spec/`: schema/validation/normalization
- `peetsfea/backend/`: Pyaedt adapters
- `examples/`: TOML examples
- `docs/`: spec/design docs
