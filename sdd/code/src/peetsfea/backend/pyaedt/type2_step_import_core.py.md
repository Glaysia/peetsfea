---
title: type2_step_import_core.py
created: 2026-04-18 @ 09:09
updated: 2026-05-03 @ 00:00
tags:
  - import
  - pyaedt
---

# type2_step_import_core.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_core.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py.md`
- Status: active
- Primary graph owner: [type2-step-import-boundary](../../../../../architecture/type2-step-import-boundary.md)

## 역할
- STEP import, ownership partition, styling handoff, imported ledger assembly를 조율한다.
- 0.2.24 SDD 기준 RX modeled import와 non-modeled guide/context import만 active contract로 둔다.

## 입력 / 출력
- 입력: STEP path, export ledger, HFSS session
- 출력: imported ownership result and imported ledger

## Canonical state
- RX imported body names are exact export contract names.
- `tx_region` guide objects may be imported as non-modeled context only.
- Import core does not heal or infer missing geometry.

## Invariants / fail-fast
- `import_3d_cad`, save, or PyAEDT false returns fail immediately.
- Missing RX bodies or generic name drift fails immediately.
- RxOnly import must not require TX modeled geometry or TX port sheets.

## Graph links
- Primary owner: [type2-step-import-boundary](../../../../../architecture/type2-step-import-boundary.md)
- [type2_step_import_partition.py](type2_step_import_partition.py.md)
- [type2_step_import_style.py](type2_step_import_style.py.md)
- [type2_step_import_ledger.py](type2_step_import_ledger.py.md)
- Representative verification: [test_type2_step_import_pipeline.py](../../../../tests/backend_em/test_type2_step_import_pipeline.py.md)
