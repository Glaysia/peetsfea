---
title: type2_step_import_partition.py
created: 2026-04-18 @ 09:09
updated: 2026-05-03 @ 23:00
tags:
  - import
  - pyaedt
---

# type2_step_import_partition.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_partition.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py.md`
- Status: active
- Primary graph owner: [type2-step-import-boundary](../../../../../architecture/type2-step-import-boundary.md)

## 역할
- Imported object names를 modeled/non-modeled ownership buckets로 분류한다.
- `tx_inner_single_coil` exact `tx_inner_*` body names and `tx_outer_single_coil` exact `tx_outer_*` body names are valid geometry-only modeled imports.

## 입력 / 출력
- 입력: export ledger expected names/groups, imported object names
- 출력: partitioned ownership result

## Canonical state
- RX conductor and RX context names are exact.
- `tx_region` is non-modeled guide context only.
- `tx_inner_pcb_l*`, `tx_inner_copper_l*`, `tx_inner_copper_stack`, `tx_underlay_pet_psa_u*`, `tx_underlay_ferrite_u*`, `tx_void_pet_psa_u*`, `tx_void_ferrite_u*`, `tx_outer_pcb_l*`, `tx_outer_copper_l*`, `tx_outer_copper_stack`, `tx_outer_void_pet_psa_u*`, `tx_outer_void_ferrite_u*`, `tx_outer_underlay_pet_psa_u*`, and `tx_outer_underlay_ferrite_u*` are recognized only for imported geometry ownership; setup-ready filtering decides whether they participate in EM.
- `tx_inner_single_coil` may carry a `g_ferrite_tx` body group for actual-region underlay and void-stack members, with member order matching export order. `tx_outer_single_coil` may carry an outer-specific passive ferrite group for outer void-stack and bottom-underlay members.

## Invariants / fail-fast
- Missing required RX bodies fail immediately.
- Missing required `tx_inner_single_coil` or `tx_outer_single_coil` geometry bodies fail immediately when the ledger declares that geometry-only modeled object.
- Unknown generic bodies fail immediately.
- RxOnly partition may validate declared geometry-only TX inner bodies, but must not synthesize TX setup inputs.

## Graph links
- Primary owner: [type2-step-import-boundary](../../../../../architecture/type2-step-import-boundary.md)
- Direct handoff: [type2_step_import_core.py](type2_step_import_core.py.md)
- Related plan: [0.2.24 Type2 TX Inner Actual Underlay Stack](../../../../../plans/0.2.24-type2-tx-inner-actual-underlay-stack.md)
- Related plan: [0.2.24 Type2 TX Inner Void YZ Stack](../../../../../plans/0.2.24-type2-tx-inner-void-yz-stack.md)
- Related plan: [0.2.24 Type2 TX Outer Void Stack](../../../../../plans/0.2.24-type2-tx-outer-void-stack.md)
