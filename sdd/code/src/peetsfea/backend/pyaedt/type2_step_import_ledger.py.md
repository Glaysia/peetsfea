---
title: type2_step_import_ledger.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - import
  - pyaedt
---

# type2_step_import_ledger.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_ledger.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py.md`
- Status: active

## 역할
- STEP import 결과를 imported ledger로 직렬화한다.
- 0.2.24 SDD 기준 RX ownership과 non-modeled guide/context ownership만 문서화한다.

## 입력 / 출력
- 입력: export ledger, imported object names, ownership partition result
- 출력: `type2_imported_ledger.json`

## Canonical state
- Imported ledger records source paths, seed, imported ownership, and imported object names.
- Imported ledger does not own mesh, boundary, port, or report summary state.
- `tx_region` may appear as a non-modeled guide object; it is not TX modeled geometry.

## Invariants / fail-fast
- Missing required RX imported bodies fail immediately.
- Generic imported-name drift is a contract failure.
- RxOnly imported ledger must not require TX modeled entries.

## Collaborators
- [type2_step_import_core.py](type2_step_import_core.py.md)
- [type2_step_ledger.py](../../type2_step_ledger.py.md)
