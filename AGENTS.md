---
title: AGENTS
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 20:35
tags:
  - governance
---

> Global code commandments live in [CODE_COMMANDMENTS.md](CODE_COMMANDMENTS.md) and are mandatory for the entire repository.
> Commandment 1 is active now: every real failure must raise and stop execution by default.
> Commandment 2 is active now: if a PyAEDT call returns `False`, raise immediately with context; never log-and-continue.
> Commandment 3 is active now for all `src/`: repository runtime state must not be nullable.
> Commandment 4 is active now for `src/`: bind values only after asserted validation.
> Commandment 5 is active now for `src/`: attribute and mapping fallbacks are forbidden.
> Fallbacks are forbidden: do not add fallback code paths, degraded substitutes, silent retries, or "try alternative behavior and continue" logic unless the user explicitly requests that behavior for the current task.
> After any AEDT/PyAEDT-affecting code change, run a real headless AEDT validation from `run/` before calling the work complete. If the local AEDT/license/runtime cannot run, report the blocker and leave the work explicitly incomplete; do not hand unvalidated AEDT code to the user as done.
> SDD policy lives in [SDD.md](SDD.md).
> From `0.2.22` onward, any newly created or substantively edited tracked Python file under `src/`, `entry/`, or `tests/` must ship with a matching note under `sdd/code/`.
# AGENTS

This document defines the project rules for coding agents working in this repository.

## Project goals
- **Spec-first design**: The TOML spec is the single source of truth (SSOT).
- **Determinism**: Same spec + same version + same seed => same results.
- **Pyaedt backend**: Delegate modeling/simulation to Pyaedt.
- **Dataset generation**: Produce datasets via parameter sweeps/sampling.

## Working principles
- Follow the repository-wide commandments in `CODE_COMMANDMENTS.md`; this document supplements them and must not weaken them.
- Current active design work is `type2`. `type1` is deprecated/frozen legacy state; do not modify `type1` code, docs, examples, tests, or spec artifacts unless the user explicitly asks for `type1` work in the current task. Legacy `type1` paths live under explicit legacy boundaries such as `src/peetsfea/legacy/type1/`, `entry/legacy/type1/`, `tests/legacy/type1/`, `examples/legacy/`, and `docs/legacy/`.
- Multiple agents may work in this repository concurrently; before editing, re-read any file that may have changed, keep changes scoped to the assigned task, and do not overwrite, revert, or reformat unrelated in-flight edits from other agents.
- Coordinate by preserving other agents' in-flight work and integrating around it instead of forcing a file back to an earlier local snapshot.
- Keep small, tightly coupled edits local. When a requested change spans multiple subsystems, independent write sets, or enough files that parallel work would reduce risk or turnaround time, split the work across subagents with explicit file/module ownership instead of doing everything in one agent.
- Do not implement fallback behavior by default. If the intended path fails or is unsupported, raise immediately with actionable context instead of switching to an alternate path.
- In `src/`, do not introduce `Optional[...]`, `| None`, `NotRequired[...]`, `if value is None`, or `if value is not None` for repository runtime state, including parser and boundary code.
- In `src/`, validate dynamic values before binding them: `assert hasattr(...)`, read, then `assert isinstance(...)` or assert an equivalent invariant.
- In `src/`, do not use `getattr(..., default)`, `mapping.get(...)`, or similar fallback-return APIs for required state, including parser and boundary code.
- If state must survive across steps, prefer a canonical module-level registry/dictionary and require `assert key in registry` before reads.
- Any spec change must be reflected in docs (README or spec docs).
- Random/sampling logic must always accept an explicit `seed`.
- Document defaults; do not hide implicit values.
- Keep Pyaedt-dependent code isolated and replaceable.
- Headless AEDT is the required validation target for AEDT/PyAEDT behavior. GUI-visible AEDT may be used only as an additional inspection aid; it never replaces a successful headless validation.
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
- Tracked Python files under `src/` or `entry/` that exceed 800 lines are strong split candidates. When substantively editing one, first assess whether the change should reduce size by splitting along ownership boundaries instead of extending the oversized file.
- Keep the TOML-to-code mapping one-to-one; avoid generating multiple code paths per spec.
- Ensure (TOML + seed) deterministically maps to final parameters; treat this as a testable contract.
- Preflight validation must report what is supported vs. unsupported before design generation.

## SDD rules
- `SDD.md` is the repository policy for software design documentation. Follow it together with `AGENTS.md`, `README.md`, and `CODE_COMMANDMENTS.md`.
- Scope: the forward-only SDD requirement applies from `0.2.22` onward to newly created or substantively edited tracked Python files under `src/`, `entry/`, and `tests/`.
- Legacy tracked files that remain untouched are exempt. Once a legacy file is substantively edited, add or update the matching `sdd/code/<repo-relative-path>.md` note in the same change.
- Required code-note mapping examples:
  - `src/peetsfea/spec/loader.py` -> `sdd/code/src/peetsfea/spec/loader.py.md`
  - `entry/legacy/type1/sample.py` -> `sdd/code/entry/sample.py.md`
  - `tests/legacy/type1/spec_resolver/test_sampling_registry.py` -> `sdd/code/tests/spec_resolver/test_sampling_registry.py.md`
- A substantive edit includes changes to logic, interfaces, runtime state, invariants, I/O, fail-fast behavior, or data flow. Formatting-only, comment-only, or purely mechanical non-behavioral changes do not trigger mandatory note updates.
- Every code note must state the source path, single responsibility, inputs/outputs, canonical state, invariants, fail-fast points, collaborator modules, related tests, change hazards, and relevant Markdown relative-link connections.
- For any substantive edit to tracked Python under `src/`, `entry/`, or `tests/`, update or create the matching `sdd/code/...md` note before editing the Python code whenever feasible. Do not defer SDD note updates until after the code change unless the user explicitly asks to postpone documentation work for the current task.
- New features and large refactors must create or update a plan note under `sdd/plans/` before or alongside the code change.
- For `src/` or `entry/` size-driven refactors, treat the 800-line threshold as a strong guideline rather than a hard cap. Exceptions should be justified by documented ownership boundaries instead of convenience.
- If splitting a tracked Python file creates new tracked Python files, add the matching `sdd/code/<repo-relative-path>.md` notes in the same change and update the original file's note to match its reduced responsibility.
- When a size-driven split is being prepared for parallel implementation, create the planned `sdd/code/<repo-relative-path>.md` notes for the target files before code lands so other agents can implement against the documented boundaries.
- If module boundaries, flows, or layering change, also create or update the relevant notes under `sdd/architecture/`, `sdd/structure/`, or `sdd/diagrams/`.
- When a size-driven split changes module boundaries or collaboration flow, update the relevant `sdd/plans/` note and any affected `sdd/architecture/` or `sdd/structure/` note in the same change.
- `tests/` remain in scope for ordinary SDD code-note coverage, but they are excluded from the 800-line split-threshold rule.
- Use Markdown links to actual `.md` files for meaningful relationships only: parent/child index structure, direct collaborator modules, direct tests, directly related plans, and concrete architecture/diagram notes. Do not repeat global policy or hub links in every note. Prefer path-qualified relative links such as `[loader.py](sdd/code/src/peetsfea/spec/loader.py.md)` to avoid ambiguity.
- Do not backfill the entire repository unless the user explicitly asks for it. The default policy is forward-only SDD coverage from `0.2.22` onward.

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
- Treat `type1` TOML/spec material as legacy reference only unless the user explicitly requests `type1` maintenance. New spec/example work should target the active `type2` path.

## Tests/execution
- Prefer pure-Python tests for the spec parser/validator.
- Separate integration tests that require Pyaedt, but run them for every code change that affects AEDT/PyAEDT import, ports, setup, solve, reports, materials, validation, or runtime entrypoints.
- Do not include large dataset generation in default test runs.
- Determinism tests are required. Pyaedt integration tests are mandatory for AEDT/PyAEDT-affecting changes.
- Run commands from the `run/` directory when executing scripts/tests to avoid polluting the repo root with generated artifacts.
- Prefer output paths under `run/` for manifests, AEDT files, logs, and temporary execution artifacts.
- Active default execution should use type2 entrypoints. Frozen `type1` batch/runtime flows are legacy-only and live under `entry/legacy/type1/`.
- Do not run those entry scripts directly from arbitrary cwd without the matching cleanup step.
- Default execution and agent validation must stay headless. Do not treat GUI-visible AEDT behavior as completion evidence for implementation work.
- After editing AEDT/PyAEDT code or an entrypoint that can launch AEDT, run the relevant real headless AEDT test or build command from `run/` using `.venv`. If it fails, fix the code and rerun. If the local machine cannot start AEDT or lacks a usable license, stop and report the exact blocker.
- GUI-visible AEDT checks are allowed as extra diagnosis, but they are never a substitute for headless AEDT validation.
- Ad-hoc GUI observations must not be used to claim product/runtime correctness unless a matching headless validation has already passed.
- Required sequence:
  - For active type2 import/debug work, run the `run-type2-import-debug` task or launch `Run entry/import_type2_step.py from run/`.
  - Frozen type1 TOML generation uses the `legacy-type1-run-sample-debug` task and `../entry/legacy/type1/sample.py`.
  - Frozen type1 AEDT generation from existing batch manifests uses `../.venv/bin/python ../entry/legacy/type1/build.py` from `run/` after `prepare-build-debug`.
  - Frozen type1 GUI validation uses `legacy-type1 Run entry/sample_build.py from run/`; its `preLaunchTask` is `prepare-build-debug`, so it clears `run/aedt/` before starting.
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
- `sdd/`: Obsidian-targeted SDD workspace and code/design note registry
