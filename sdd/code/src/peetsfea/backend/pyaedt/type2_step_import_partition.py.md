---
title: type2_step_import_partition.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 13:10
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
- Imported object names를 modeled/non-modeled ownership buckets로 분류한다.
- `tx_inner_single_coil` exact `tx_inner_*` body names are valid geometry-only modeled imports.

## 입력 / 출력
- 입력: export ledger expected names/groups, imported object names
- 출력: partitioned ownership result

## Canonical state
- RX conductor and RX context names are exact.
- `tx_region` is non-modeled guide context only.
- `tx_inner_pcb_l*`, `tx_inner_copper_l*`, and `tx_inner_copper_stack` are recognized only for imported geometry ownership; setup-ready filtering decides whether they participate in EM.

## Invariants / fail-fast
- Missing required RX bodies fail immediately.
- Missing required `tx_inner_single_coil` geometry bodies fail immediately when the ledger declares that geometry-only modeled object.
- Unknown generic bodies fail immediately.
- RxOnly partition may validate declared geometry-only TX inner bodies, but must not synthesize TX setup inputs.

## Collaborators
- [type2_step_import_core.py](type2_step_import_core.py.md)
