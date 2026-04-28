---
title: type2_step_import_partition.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - import
  - pyaedt
---

# type2_step_import_partition.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_partition.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py.md`
- Status: active

## 역할
- Imported object names를 RX conductor/context/non-modeled guide buckets로 분류한다.
- TX shape-specific partitioning is not part of the 0.2.24 SDD contract.

## 입력 / 출력
- 입력: export ledger expected names/groups, imported object names
- 출력: partitioned ownership result

## Canonical state
- RX conductor and RX context names are exact.
- `tx_region` is non-modeled guide context only.

## Invariants / fail-fast
- Missing required RX bodies fail immediately.
- Unknown generic bodies fail immediately.
- RxOnly partition must not require TX modeled bodies.

## Collaborators
- [type2_step_import_core.py](type2_step_import_core.py.md)
