---
title: type2_step_import_style.py
created: 2026-04-18 @ 09:09
updated: 2026-05-04 @ 00:00
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
- Imported TX outer conductor/context objects are styled as geometry-only modeled bodies when declared by the ledger.
- TX inner and RX port sheet reconstruction support remains runtime metadata, not imported STEP geometry.
- TxRx mode에서 TX inner의 port sheet는 모델 입력 `terminal_metadata`의 `port_sheet_vertices_xyz`를 사용해
  `tx_inner_port_sheet`로 재구성한다.

## 입력 / 출력
- 입력: partitioned imported object groups, HFSS modeler
- 출력: styled imported objects and runtime reconstructed TX inner/RX sheet geometry where needed

## Canonical state
- RX conductor receives conductor material/styling.
- Non-modeled guide/context objects remain non-conductor context.
- RxOnly creates no TX reconstructed sheets.
- TxRx 생성 시 TX 내측 코일은 `tx_inner_port_sheet`로 재구성되며, RX는 기존 `rx_port_sheet`를 사용한다.
- TX 내측(port) 역할은 `tx_inner_single_coil`으로만 처리하며, 일반 `tx_single_coil`는 이 경로에서 제외한다.
- `tx_outer_single_coil` is allowed for imported material/visual styling but does not reconstruct a port sheet.
- `tx_outer_single_coil` bounds must be owned by `tx_outer_region`; validation accepts expected world +X protrusion and world -Z underhang from rigid tilted stacking while preserving semantic owner and Y/max-Z checks.
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
- TX outer void-stack bodies receive passive material styling: `tx_outer_void_pet_psa_u*` uses `PET_PSA`, and `tx_outer_void_ferrite_u*` uses `MULL12060ferrite`.
- TX outer bottom-underlay bodies receive passive material styling: `tx_outer_underlay_pet_psa_u*` uses `PET_PSA`, and `tx_outer_underlay_ferrite_u*` uses `MULL12060ferrite`.

## Invariants / fail-fast
- Missing required RX imported objects fail immediately.
- Styling false returns fail immediately.
- Guide/context bodies must not be treated as conductor bodies.
- `tx_inner_single_coil`는 `terminal_metadata.port_sheet_vertices_xyz` 필수이며 누락·형식 오류는 즉시 실패한다.
- `tx_outer_single_coil` must not silently become an active port/source/report participant; setup-ready filters it before active EM input construction.
- `tx_outer_single_coil` protrusion/underhang allowances are role-specific and must not weaken RX or TX inner bounds validation.
- `tx_inner_single_coil` validation must fail when the actual/design bounds escape
  `tx_inner_region`, when physical provenance diverges from modeled bounds, or when the
  physical modeled bounds escape the actual/design bounds; it must not snap, recenter, or
  infer an alternate owner.
- `tx_inner_actual_region.tx_actual_region.source_guide_id` must match
  `placement_owner_id=tx_inner_region`, and `modeled_source_id` must match the modeled
  object id.
- TX inner actual-underlay material setup must use the existing dataset ferrite material path and fail fast when dataset/material APIs are unavailable.

## Graph links
- Primary owner: [type2-step-import-boundary](../../../../../architecture/type2-step-import-boundary.md)
- Direct handoff: [type2_step_import_core.py](type2_step_import_core.py.md)
- Exceptional handoff: [type2_step_port_assignment.py](type2_step_port_assignment.py.md)
- Related plan: [0.2.24 Type2 TX Inner Actual Underlay Stack](../../../../../plans/0.2.24-type2-tx-inner-actual-underlay-stack.md)
- Related plan: [0.2.24 Type2 TX Inner Void YZ Stack](../../../../../plans/0.2.24-type2-tx-inner-void-yz-stack.md)
- Related plan: [0.2.24 Type2 TX Outer Void Stack](../../../../../plans/0.2.24-type2-tx-outer-void-stack.md)
