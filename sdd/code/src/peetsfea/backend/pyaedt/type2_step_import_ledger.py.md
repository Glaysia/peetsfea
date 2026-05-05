---
title: type2_step_import_ledger.py
created: 2026-04-18 @ 09:09
updated: 2026-05-04 @ 00:00
tags:
  - import
  - pyaedt
---

# type2_step_import_ledger.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_ledger.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py.md`
- Status: active
- Primary graph owner: [type2-step-import-boundary](../../../../../architecture/type2-step-import-boundary.md)

## 역할
- STEP import 결과를 imported ledger로 직렬화한다.
- 0.2.24 SDD 기준 RX ownership, geometry-only `tx_inner_single_coil`/`tx_outer_single_coil` ownership, and non-modeled guide/context ownership을 문서화한다.

## 입력 / 출력
- 입력: export ledger, imported object names, ownership partition result
- 출력: `type2_imported_ledger.json`

## Canonical state
- Imported ledger records source paths, seed, imported ownership, and imported object names.
- Imported ledger does not own mesh, boundary, port, or report summary state.
- `tx_region` may appear as a non-modeled guide object; it is not TX modeled geometry.
- `tx_inner_single_coil` may appear as modeled geometry with `tx_inner_region` placement ownership.
- `tx_inner_single_coil` ferrite-family group validation includes both actual-region underlay members and void-stack members in the exact export order declared by the ledger.
- `tx_outer_single_coil` may appear as modeled geometry with `tx_outer_region` placement ownership, but remains setup-inactive until a later plan defines explicit outer TX excitation semantics.
- `tx_outer_single_coil` canonical ownership metadata may include `canonical_coordinates.outer_tilt_metadata.max_world_x_protrusion_mm` and `max_world_z_underhang_mm` only; both numeric non-negative contracts are required for strict provenance and validated when the outer role is present.
- `tx_outer_single_coil` may include passive outer void-stack ferrite/PET bodies, passive outer bottom-underlay ferrite/PET bodies, and an outer-specific passive body group. These are imported geometry ownership only and do not activate TX outer EM setup.

## Invariants / fail-fast
- Missing required RX imported bodies fail immediately.
- Missing required `tx_inner_single_coil` or `tx_outer_single_coil` imported bodies fail immediately when declared by the source ledger.
- Generic imported-name drift is a contract failure.
- RxOnly imported ledger may record geometry-only TX inner/outer entries, but setup-ready must filter them before active EM input construction.
- Outer TX outer canonical tilt metadata with wrong key set or negative values fails fast during step-ledger validation.
- Outer passive body group validation must accept `tx_outer_void_ferrite_u*`, `tx_outer_void_pet_psa_u*`, `tx_outer_underlay_ferrite_u*`, and `tx_outer_underlay_pet_psa_u*` only for the `tx_outer_single_coil` role and must reject cross-role passive body leakage.
- Tx inner void-stack group/member ordering drift fails during step-ledger validation before AEDT import.

## Graph links
- Primary owner: [type2-step-import-boundary](../../../../../architecture/type2-step-import-boundary.md)
- Direct handoff: [type2_step_import_core.py](type2_step_import_core.py.md)
- Exceptional artifact handoff: [type2_step_ledger.py](../../type2_step_ledger.py.md)
- Related plan: [0.2.24 Type2 TX Outer Void Stack](../../../../../plans/0.2.24-type2-tx-outer-void-stack.md)
