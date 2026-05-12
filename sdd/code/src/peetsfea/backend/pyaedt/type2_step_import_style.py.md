---
title: type2_step_import_style.py
created: 2026-04-18 @ 09:09
updated: 2026-05-13 @ 00:00
tags:
  - import
  - pyaedt
---

# type2_step_import_style.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_style.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py.md`
- Status: active
- Primary graph owner: [type2-step-import-boundary](../../../../../architecture/type2-step-import-boundary.md)

## 역할
- Imported RX conductor/context objects에 material/color/name styling을 적용한다.
- Imported TX inner/RX conductor/context objects에 material/color/name styling을 적용한다.
- Active import styling no longer accepts TX outer modeled entries; ledgers containing `tx_outer_single_coil` fail before styling.
- TX inner and RX port sheet creation uses the ledger `single_coil_port_v1` contract, not imported STEP geometry or post-hoc body inference.

## 입력 / 출력
- 입력: partitioned imported object groups, HFSS modeler
- 출력: styled imported objects and runtime-created TX inner/RX sheet geometry from the ledger port contract where needed

## Canonical state
- RX conductor receives conductor material/styling.
- Non-modeled guide/context objects remain non-conductor context.
- RxOnly creates no TX reconstructed sheets.
- TxRx 생성 시 TX 내측 코일은 `tx_inner_port_sheet`, RX는 `rx_port_sheet`를 runtime-created sheet로 만든다.
- TX 내측(port) 역할은 `tx_inner_single_coil`으로만 처리하며, 일반 `tx_single_coil`는 이 경로에서 제외한다.
- `tx_inner_single_coil` bounds must be owned by `tx_inner_region`, but import validation
  uses `tx_inner_actual_region.tx_actual_region` as the design bounds contract.
- `tx_inner_actual_region` design bounds must match the member canonical coordinates, stay
  contained in `tx_inner_region` X/Y, remain centered in owner Y, and remain top-aligned
  against owner max Z.
- `tx_inner_actual_region.tx_actual_region.physical_modeled_body_bounds` must match the
  modeled `tx_inner_single_coil` ledger bounds and remain contained inside the actual/design
  bounds.
- TX inner actual-underlay bodies receive passive material styling: `tx_underlay_pet_psa_u*` uses `PET_PSA`, and `tx_underlay_ferrite_u*` uses `MULL12060ferrite`.
- TX inner void-stack bodies receive passive material styling: `tx_void_pet_psa_u*` uses `PET_PSA`, and `tx_void_ferrite_u*` uses `MULL12060ferrite`.
- `tv_aluminum_plate` is created as a runtime HFSS sheet from canonical `sheet_vertices_xyz` only when `sheet_present == 1`; import styling applies visual state only, with no finite-conductivity boundary, volume material assignment, port sheet ownership, or imported body groups.

## Invariants / fail-fast
- Missing required RX imported objects fail immediately.
- Styling false returns fail immediately.
- Guide/context bodies must not be treated as conductor bodies.
- `tx_inner_single_coil` and `rx_single_coil` require `terminal_metadata.kind = "single_coil_port_v1"` with finite `vertices_xyz`.
- `tx_outer_single_coil` must not silently become an import/styling participant; active ledger validation rejects it.
- `tx_inner_single_coil` validation must fail when the actual/design bounds escape
  `tx_inner_region`, when physical provenance diverges from modeled bounds, or when the
  physical modeled bounds escape the actual/design bounds; it must not snap, recenter, or
  infer an alternate owner.
- `tx_inner_actual_region.tx_actual_region.source_guide_id` must match
  `placement_owner_id=tx_inner_region`, and `modeled_source_id` must match the modeled
  object id.
- TX inner actual-underlay material setup must use the existing dataset ferrite material path and fail fast when dataset/material APIs are unavailable.
- TV aluminum plate bounds must prove flush placement on the `tv` +X face, zero X thickness, full TV Y/Z span, `plane = "YZ"`, `material = "aluminum"`, and `placement_owner_id = "tv"`; sheet creation also fails if the covered AEDT sheet name drifts from `tv_aluminum_plate`.

## Graph links
- Primary owner: [type2-step-import-boundary](../../../../../architecture/type2-step-import-boundary.md)
- Direct handoff: [type2_step_import_core.py](type2_step_import_core.py.md)
- Exceptional handoff: [type2_step_port_assignment.py](type2_step_port_assignment.py.md)
- Related plan: [0.2.24 Type2 TX Inner Actual Underlay Stack](../../../../../plans/0.2.24-type2-tx-inner-actual-underlay-stack.md)
- Related plan: [0.2.24 Type2 TX Inner Void YZ Stack](../../../../../plans/0.2.24-type2-tx-inner-void-yz-stack.md)
- Related plan: [0.2.24 Type2 TX Outer Void Stack](../../../../../plans/0.2.24-type2-tx-outer-void-stack.md)
- Related plan: [0.2.24 Type2 TV Aluminum Plate](../../../../../plans/0.2.24-type2-tv-aluminum-plate.md)
- Related plan: [0.2.25 Type2 TV Aluminum Sheet Presence](../../../../../plans/0.2.25-type2-tv-aluminum-sheet-presence.md)
- Related plan: [0.2.25 Type2 Port Sheet Contract Rewrite](../../../../../plans/0.2.25-type2-port-sheet-contract-rewrite.md)
