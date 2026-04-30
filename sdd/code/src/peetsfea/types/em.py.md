---
title: em.py
created: 2026-04-29 @ 00:00
updated: 2026-04-29 @ 00:00
tags:
  - types
  - em
---

# em.py

## Source
- Path: `src/peetsfea/types/em.py`
- Code note path: `sdd/code/src/peetsfea/types/em.py.md`
- Status: active

## 역할
- EM pipeline, output report, port assignment, and report template shared `TypedDict` contracts를 정의한다.

## 입력 / 출력
- 입력: parser/backend modules가 공유하는 Python mapping-shaped runtime records.
- 출력: concrete `TypedDict` contracts exported through `peetsfea.types.manifest` and `peetsfea.types`.

## Canonical state
- `OutputsSpec.mode` is required and identifies the active output contract such as `RxOnly` or `TxRx`.
- `OutputsSpec.variables` contains validated `OutputVariableSpec` entries.
- EM port and assignment typed dicts keep TX/RX slots explicit.

## Invariants
- Runtime state is not nullable.
- Required TOML/ledger state must be represented as required typed fields, not optional fallbacks.
- Output mode is part of the SSOT report contract and must not be inferred from variable names downstream.

## Fail-fast points
- This module defines shapes only; parser and backend modules perform runtime validation.

## Collaborators
- [outputs.py](../spec/outputs.py.md)
- [type2_step_setup_ready.py](../backend/pyaedt/type2_step_setup_ready.py.md)

## Related tests
- [test_type2_step_spec_import_surface.py](../../../tests/type2/test_type2_step_spec_import_surface.py.md)
- [test_type2_step_setup_ready.py](../../../tests/backend_em/test_type2_step_setup_ready.py.md)

## Change hazards
- Adding or removing required fields affects TOML parsing, STEP ledger loading, and backend report setup.
- Keep this type contract synchronized with `parse_outputs_table`.

