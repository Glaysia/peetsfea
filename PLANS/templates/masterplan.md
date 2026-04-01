# CODE_COMMANDMENTS Master Plan Template

Use this template for a repo-wide multi-step `CODE_COMMANDMENTS` rollout in `peetsfea`.

Master Plan Status: `Not Started`

## Objective
- State the repository-wide behavior change in 2-4 sentences.
- State what “done” means without leaving ordering decisions to the implementer.

## Repo-Wide Invariants
- Follow `CODE_COMMANDMENTS.md` and `AGENTS.md`.
- Use `.venv` for Python commands.
- Run script/test commands from `run/` when execution is needed.
- Keep default AEDT execution headless.
- Do not allow silent recovery, log-and-continue, or failure sentinel contracts in orchestration or external-boundary code.
- Keep valid domain predicates as booleans; only failure sentinels must be eliminated.

## Locked Deliverables
- Concrete markdown deliverables this master plan must produce:
- Concrete code deliverables this master plan must eventually produce:
- Final audit artifacts or summaries required before closure:

## Current Hotspots
- List the known code areas that justify the rollout and why each matters.

## Rollout Slices
- Group the implementation into coherent workstreams with clear boundaries.
- Each slice must be small enough to map to one or more numbered subplans.

## Subplan Backlog
Use one row per subplan in execution order.

| Order | Subplan File | Commandment Focus | Primary Objective | Locked Touch Points | Status |
| --- | --- | --- | --- | --- | --- |
| 01 | `PLANS/repeat/<masterplan_slug>_01_<topic>.md` | `1` / `2` / `both` |  |  | `Not Started` |

Naming rule:
- Concrete subplans live under `PLANS/repeat/`.
- Use `<masterplan_slug>_<NN>_<short_topic>.md`.
- Keep numbering stable once published.

## Public API / Behavior Contract Changes
- List user-visible or internal contract changes that the rollout locks in.
- Explicitly separate:
  - failure paths that must raise
  - boolean predicates that remain valid

## Verification Matrix
- Per-slice pytest targets:
- Per-slice static/type checks:
- Manual audit checks:
- Final full-suite command(s):
  - `cd run && ../.venv/bin/pytest ../tests`
  - `cd run && ../.venv/bin/pyright`

## Stop Conditions
- Conditions that require stopping the chain and revising the master plan:

## Final Acceptance
- Concrete conditions required before the master plan can be marked `Complete`:

## Progress Log
- Record completed subplans, blocked subplans, contract decisions, and changed assumptions:
