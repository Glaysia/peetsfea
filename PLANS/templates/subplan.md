# CODE_COMMANDMENTS Subplan Template

Use this template for each concrete rollout step under a `CODE_COMMANDMENTS` master plan in `peetsfea`.

Execution Status: `Not Started`

## Invariant Rules
- Execute one primary objective only.
- Keep the step inside the active master plan; do not fork a new rollout.
- Use the repository `.venv` for Python commands.
- When execution is needed, run script/test commands from `run/`.
- Default AEDT execution stays headless; do not use GUI AEDT unless the user explicitly requested it.
- Do not log-and-continue, skip failures, or convert real failures into `False`/`None`.
- Classify every touched boolean as either:
  - a valid domain predicate that remains boolean, or
  - a forbidden failure sentinel that must be replaced by exception-first behavior.
- If the step exposes a broader architectural issue than its own objective, stop and escalate to the parent master plan instead of widening scope.
- Create the next subplan file only after the current step is complete or blocked with explicit handoff notes.

## 0. Carryovers From the Previous Step
- Previous subplan file:
- Frozen inputs inherited from the previous step:
- Current repo facts that still matter:

## 1. Single Objective
- One sentence only:

## 2. Commandment Focus
- Commandment scope: `1` / `2` / `both`
- Why this step cannot be split further without losing coherence:

## 3. Locked Inputs
- Source files, docs, tests, contracts, or baseline audit notes this step is allowed to trust:

## 4. Locked Non-Scope Regions
- Files or behaviors that must not be changed in this step:

## 5. Planned Touch Points
- Expected `src/` files:
- Expected `entry/` files:
- Expected `tests/` files:
- Expected docs/plan files:

## 6. Failure-Signal Audit
- Failure sentinels to remove in this step:
- Boolean predicates that must remain booleans:
- Shared helper or contract changes required:
- Broad `except` blocks that are allowed cleanup/probing only:

## 7. Required Verification
- Working directory:
  - `run/`
- Targeted pytest command(s):
  - `../.venv/bin/pytest ...`
- Type check command:
  - `../.venv/bin/pyright`
- Manual audit checks:
  - verify no new log-and-continue path was introduced
  - verify touched failure paths raise with context

## 8. Stop and Escalate Conditions
- Conditions that force a stop instead of another local iteration:

## 9. Completion Criteria
- Concrete conditions that must be true before this step can close:

## 10. Execution Record
- Source files actually modified:
- Test files actually modified:
- Docs/plan files actually modified:
- Verification actually run:
- Failure sentinels removed:
- Predicate booleans preserved:
- Remaining issues:
- Escalations or new risks:

## 11. Next Step
- Next subplan file:
- Next subplan objective:
- Handoff constraints for the next step:

## 12. Prohibited Actions
- Do not widen scope beyond the single objective.
- Do not treat a normal domain predicate as a failure just because it returns `False`.
- Do not keep a failure sentinel `False`/`None` contract for orchestration, IO, or PyAEDT boundary code.
- Do not weaken headless AEDT rules or AGENTS.md execution rules.
- Do not treat cleanup-only `finally` behavior as permission to swallow the original failure.
