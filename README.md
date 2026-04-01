# peetsfea

Spec-first deterministic device design and AEDT build pipeline for the `peetsfea` project.

## Development

Use the project virtual environment at `.venv` and run repository tasks from the workspace root unless a task specifies `run/` as the working directory.

Repository runtime code under `src/` is assert-driven and fail-fast by design. Do not run the project with `python -O`; optimized mode strips required assertions and is rejected on import/runtime.

Nullable runtime state and fallback attribute/mapping access are forbidden across `src/`. Required values must be asserted and bound explicitly rather than defaulted.

## Debug Launch

VS Code debug tasks in `.vscode/tasks.json` install the project in editable mode before running. This file exists so the package metadata declared in `pyproject.toml` has a valid readme target during that step.
