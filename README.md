---
title: peetsfea
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - governance
---

# peetsfea

Spec-first deterministic device design and AEDT build pipeline for the `peetsfea` project.

## Development

Use the project virtual environment at `.venv` and run repository tasks from the workspace root unless a task specifies `run/` as the working directory.

Repository runtime code under `src/` is assert-driven and fail-fast by design. Do not run the project with `python -O`; optimized mode strips required assertions and is rejected on import/runtime.

Nullable runtime state and fallback attribute/mapping access are forbidden across `src/`. Required values must be asserted and bound explicitly rather than defaulted.

`type1`은 frozen legacy다. active/default surface는 `type2`만 다루며, `type1` 관련 entry/test/doc/example은 legacy 경로에서만 opt-in으로 사용한다.

## Debug Launch

VS Code debug tasks in `.vscode/tasks.json` install the project in editable mode before running. This file exists so the package metadata declared in `pyproject.toml` has a valid readme target during that step.

## Release History

Release work may be squashed onto `main` to keep the public history compact. When that happens, topic branches can retain their detailed commit history, and later sync back to `main` through a normal merge once `main` has advanced again.
