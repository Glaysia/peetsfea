# CODE_COMMANDMENTS Rollout Master Plan

Master Plan Status: `Complete (Scoped Closure With Residual Inherited Blockers Documented)`

## Objective
- Apply `CODE_COMMANDMENTS.md` across the `peetsfea` source tree with an exception-first contract for real failures.
- Eliminate failure sentinel `False`/`None` behavior from orchestration and external-boundary code, especially the PyAEDT boundary, while preserving normal boolean-returning domain predicates such as constraints, geometry predicates, and validation helpers.
- Finish with a stable helper contract for PyAEDT fail-fast handling, updated tests, and a repo-wide audit proving that no targeted log-and-continue behavior remains in the touched rollout scope.

## Repo-Wide Invariants
- Follow `CODE_COMMANDMENTS.md` and `AGENTS.md` without weakening either document.
- Use `.venv` for Python commands.
- Run script/test commands from `run/` when execution is needed.
- Default AEDT execution stays headless; GUI AEDT is opt-in only when explicitly requested.
- Cleanup-only `finally` behavior may remain only when it does not suppress the original failure.
- Broad `except` blocks are allowed only for capability probing, compatibility shims, or cleanup paths that do not silently recover from the real failure.
- Domain predicates may remain boolean. Failure sentinels in orchestration, IO, and external-boundary code may not.

## Locked Deliverables
- Updated `PLANS/templates/subplan.md` specialized for commandment rollout work.
- Updated `PLANS/templates/masterplan.md` specialized for repo-wide commandment rollout work.
- This master plan plus a numbered subplan chain under `PLANS/repeat/`.
- Source-code changes that eliminate targeted failure sentinel contracts and add one shared internal PyAEDT fail-fast helper layer.
- Updated tests covering new exception-first behavior and preserved predicate booleans.
- Final repo-wide audit notes recorded in the closing subplan.

## Current Hotspots
- `entry/sample.py` currently catches exceptions and skips failed seeds via log-and-continue behavior.
- `src/peetsfea/pipeline/run_batch.py` currently returns `False` on build failure and exposes `raise_on_error=False` compatibility paths that conflict with the commandment baseline.
- `src/peetsfea/backend/pyaedt/geometry/build.py` and `src/peetsfea/backend/pyaedt/geometry/build_rx_dd.py` still contain unchecked or unevenly checked PyAEDT calls such as `save_project`.
- `src/peetsfea/backend/pyaedt/geometry/scene_objects.py`, `src/peetsfea/backend/pyaedt/geometry/cad_probe.py`, and `src/peetsfea/backend/pyaedt/em_pipeline/analysis.py` contain broad exception handling that must be classified as allowed cleanup/probing behavior or removed.

## Rollout Slices
- Baseline audit and helper contract:
  lock the boolean-classification rule and define the shared PyAEDT fail-fast helper interface.
- Sampling and batch orchestration fail-fast:
  remove skip-and-continue behavior and sentinel failure return values from sample/build batch orchestration.
- Build entrypoint runtime contract alignment:
  keep headless/GUI behavior intact while making entrypoints exception-first.
- Geometry PyAEDT boundary hardening:
  route unchecked PyAEDT result handling through explicit checks or the shared helper.
- EM pipeline and capability-probing audit:
  review broad exception handling and keep only legitimate probing/cleanup cases.
- Test and audit closure:
  update tests and close the rollout with explicit audit evidence.

## Subplan Backlog

| Order | Subplan File | Commandment Focus | Primary Objective | Locked Touch Points | Status |
| --- | --- | --- | --- | --- | --- |
| 01 | `PLANS/repeat/code_commandments_rollout_01_baseline_audit_and_helper_contract.md` | `both` | Audit current failure signaling, define one internal PyAEDT fail-fast helper layer, and lock the predicate-vs-failure classification rule. | `src/peetsfea/backend/pyaedt/`, `CODE_COMMANDMENTS.md`, `tests/` audit targets | `Complete` |
| 02 | `PLANS/repeat/code_commandments_rollout_02_sampling_and_batch_failfast.md` | `1` | Remove skip-and-continue behavior from `entry/sample.py` and eliminate `False` failure outcomes from `src/peetsfea/pipeline/run_batch.py` while keeping low-churn success-path shapes only where safe. | `entry/sample.py`, `src/peetsfea/pipeline/run_batch.py`, `tests/test_run_script_artifacts.py` | `Complete` |
| 03 | `PLANS/repeat/code_commandments_rollout_03_build_entrypoints_and_runtime_contracts.md` | `1` | Align `entry/build.py` and `entry/sample_build.py` with exception-first behavior and stop-on-error defaults without weakening headless/GUI execution rules. | `entry/build.py`, `entry/sample_build.py`, entrypoint tests | `Complete` |
| 04 | `PLANS/repeat/code_commandments_rollout_04_geometry_pyaedt_boundary_hardening.md` | `2` | Route unchecked PyAEDT operations in geometry builders through explicit checks or the shared helper, including save/group/subtract/object-creation paths and `safe_unite`-style helpers. | `src/peetsfea/backend/pyaedt/geometry/` and geometry tests | `Complete` |
| 05 | `PLANS/repeat/code_commandments_rollout_05_em_pipeline_and_capability_probing_audit.md` | `both` | Harden EM boundary operations and review broad `except` blocks so only cleanup-only or capability-probing exceptions remain tolerated. | `src/peetsfea/backend/pyaedt/em_pipeline/`, `scene_objects.py`, `cad_probe.py`, EM tests | `Complete` |
| 06 | `PLANS/repeat/code_commandments_rollout_06_tests_and_audit_closure.md` | `both` | Update tests that currently expect `False` or skip behavior, add coverage for the new fail-fast helper behavior, and close with a repo-wide audit checklist. | `tests/`, audit notes, any minimal doc follow-up | `Complete` |

Naming rule:
- Concrete subplans live under `PLANS/repeat/`.
- Use `code_commandments_rollout_<NN>_<short_topic>.md`.
- Keep numbering stable once published.

## Public API / Behavior Contract Changes
- Orchestration helpers must not use `False` or `None` as failure contracts. Real failures raise.
- A single internal helper interface under `src/peetsfea/backend/pyaedt/` will convert “PyAEDT returned `False`” into a raised exception with context.
- Success-path return values may stay structured when they are not failure sentinels.
- Normal boolean-returning domain predicates remain valid when `False` means “rule not satisfied” rather than “operation failed.”

## Verification Matrix
- Subplan 01:
  audit only, plus targeted tests for the helper contract once introduced.
- Subplan 02:
  `cd run && ../.venv/bin/pytest ../tests/test_run_script_artifacts.py`
- Subplan 03:
  `cd run && ../.venv/bin/pytest ../tests/test_run_script_artifacts.py ../tests/test_entrypoint_configs.py`
- Subplan 04:
  `cd run && ../.venv/bin/pytest ../tests/test_one_turn_geometry_build.py ../tests/test_tx_port_failfast.py ../tests/test_ferrite_geometry.py`
- Subplan 05:
  `cd run && ../.venv/bin/pytest ../tests/test_em_pipeline.py ../tests/test_em_pipeline_sources.py`
- Subplan 06:
  `cd run && ../.venv/bin/pytest ../tests`
  `cd run && ../.venv/bin/pyright`
- Manual audit checks for every code-touching subplan:
  verify touched failure paths raise with context
  verify no new log-and-continue path was introduced
  verify preserved boolean predicates are still modeled as predicates, not exceptions

## Stop Conditions
- A subplan discovers that a targeted boolean is actually shared between predicate logic and failure signaling in multiple subsystems and needs a broader contract rewrite.
- A required compatibility path would force silent recovery or sentinel failure returns to remain in active orchestration code.
- A PyAEDT compatibility shim cannot distinguish capability probing from real runtime failure without first changing a broader backend contract.
- A test fixture currently encodes contradictory expectations about fail-fast behavior that cannot be resolved within the active subplan’s touch scope.

## Final Acceptance
- All six numbered subplans are either completed or explicitly retired and replaced by a renumbered approved backlog entry.
- No targeted orchestration or PyAEDT boundary code in rollout scope returns `False`/`None` to signal failure.
- The shared PyAEDT helper layer is used wherever a targeted PyAEDT call can report failure by returning `False`.
- Updated tests cover both:
  - exception-first behavior for real failures
  - preserved boolean predicates where `False` remains valid business logic
- Final verification passes:
  - `cd run && ../.venv/bin/pytest ../tests`
  - `cd run && ../.venv/bin/pyright`

## Progress Log
- Subplan file created:
  - `PLANS/repeat/code_commandments_rollout_01_baseline_audit_and_helper_contract.md`
- Subplan 01 completed:
  - shared helper contract added at `src/peetsfea/backend/pyaedt/failfast.py`
  - focused helper tests added at `tests/test_pyaedt_failfast.py`
  - targeted pyright for new files passed; full-repo pyright still has pre-existing geometry typing blockers outside Subplan 01 scope
- Next subplan:
  - `PLANS/repeat/code_commandments_rollout_03_build_entrypoints_and_runtime_contracts.md`
- Subplan 02 completed:
  - sampling no longer skips failed seeds by returning `None`
  - batch build helpers no longer use `False` as a failure outcome
  - `tests/test_run_script_artifacts.py` and targeted pyright checks passed for the touched files
- Subplan 03 completed:
  - build entrypoints now reject `stop_on_error=False` instead of treating it as a normal runtime mode
  - GUI/headless runtime selection behavior stayed intact
  - `tests/test_run_script_artifacts.py` and targeted pyright checks passed for the touched files
- Next subplan:
  - `PLANS/repeat/code_commandments_rollout_05_em_pipeline_and_capability_probing_audit.md`
- Subplan 04 completed:
  - touched geometry-layer `create_group`, `save_project`, `create_box`, and `unite` paths now raise through the shared helper
  - focused helper-adoption tests and targeted pyright checks passed for the touched geometry files
  - broader geometry suites still contain inherited blockers recorded as residual audit items
- Subplan 05 completed:
  - touched EM boundary operations now use the shared helper instead of ad-hoc falsy checks
  - probing fallbacks in analysis/cad-probe remain explicitly capability-oriented
  - focused EM tests and targeted pyright checks passed for the touched files
- Subplan 06 completed:
  - closure audit finalized with explicit residual-blocker accounting
  - all rollout subplans are now closed for the touched CODE_COMMANDMENTS scope
  - inherited broader geometry regression/type debt remains documented as follow-up work, not silently marked fixed
- Follow-up handoff:
  - residual geometry regression/type debt continues in `PLANS/repeat/code_commandments_followup_geometry_debt_masterplan.md`
- Completion summary:
  - see `PLANS/repeat/code_commandments_rollout_completion_summary.md`
