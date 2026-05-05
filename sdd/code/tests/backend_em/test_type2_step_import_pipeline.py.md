---
title: test_type2_step_import_pipeline.py
created: 2026-04-18 @ 09:09
updated: 2026-05-04 @ 00:00
tags:
  - test
  - import
---

# test_type2_step_import_pipeline.py

## Source
- Path: `tests/backend_em/test_type2_step_import_pipeline.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_step_import_pipeline.py.md`
- Status: active
- Primary graph owner: [type2-step-import-boundary](../../../architecture/type2-step-import-boundary.md)

## 역할
- type2 STEP import-only pipeline behavior를 검증한다.
- 0.2.24 SDD 기준 RX modeled import and non-modeled guide/context import are active.
- `tx_outer_single_coil`의 world +X rigid-tilt protrusion 허용 조건과 관련된 바운드 검증 회로를 커버한다.

## Canonical state
- Import ledger preserves source paths, seed, imported ownership, and imported object names.
- Import-only path must not create boundary, ports, mesh, or reports.
- `tx_region` may be carried as guide context only.
- Geometry-only `tx_inner_single_coil` import partition accepts an empty body-group contract.
- `tx_inner_single_coil` actual-underlay fixtures require `g_ferrite_tx` member order to match export order: `tx_underlay_pet_psa_u*` before `tx_underlay_ferrite_u*`.
- `tx_inner_single_coil` void-stack fixtures require `g_ferrite_tx` member order to include `tx_void_ferrite_u*` and `tx_void_pet_psa_u*` exactly as export declares them.
- STEP ledger load coverage verifies the same TX inner void-stack group contract before PyAEDT import begins.
- TX inner underlay import fixtures include the non-modeled `tx_inner_region` owner and `tx_inner_actual_region` provenance before import-bound validation runs.
- TX inner actual-region regression coverage preserves a large guide owner with a centered design/actual region and a smaller asymmetric physical modeled bbox, matching sampled TxRx debug failures.
- TX inner import fixtures include the derived non-modeled `tx_inner_actual_region` member with `tx_actual_region` provenance whenever `tx_inner_single_coil` validation requires the design/actual bounds contract.
- `tx_inner_single_coil` bounds coverage accepts sampled owner-local X placement inside `tx_inner_region` while requiring physical modeled bounds provenance to match the modeled ledger entry.
- TX inner actual-region regression coverage accepts centered design bounds at Y `[-84, 84]` when the recorded physical modeled bounds are smaller and asymmetric, such as `min_y=-84.0` and `size_y=164.07134831460672`.
- Ledger fixtures declare `outputs.mode = "RxOnly"` and only active RX output variables.
- `tx_outer_single_coil`의 tilt metadata는 `canonical_coordinates.outer_tilt_metadata.max_world_x_protrusion_mm` 및 `max_world_z_underhang_mm` 키로만 제공되며, 값은 0 이상의 숫자여야 한다.
- `tx_outer_single_coil` fixtures may include outer void-stack passive bodies, outer bottom-underlay passive bodies, and an outer-specific passive body group; these must import/style as passive geometry without activating TX outer setup.
- `tx_outer_void_ferrite_u*` and `tx_outer_void_pet_psa_u*` import fixtures may reach `tx_region.max_z`; import/setup still treats that height as passive geometry metadata, not as a TOML/schema/import-role change.
- Tx terminal bridge members are allowed as non-model scene members (`tx_pos_bridge_pcb`, `tx_pos_bridge_copper`, `tx_neg_bridge_pcb`, `tx_neg_bridge_copper`) and must stay in non-modeled buckets.

## Invariants / fail-fast
- Missing RX imported bodies and generic imported names fail.
- RxOnly import tests must not require TX modeled bodies.
- `tx_outer_single_coil` without `outer_tilt_metadata` must fail strict X-overrun check.
- `tx_outer_single_coil` malformed or negative `outer_tilt_metadata` must fail parsing/validation with no fallback.
- Tx bridge member IDs must be claimed by `type2_non_model_scene` partitioning and cannot appear in modeled body assignments.
- `tx_outer_single_coil` fixtures with inner-only ferrite-family expected members must fail before import grouping can treat those passive bodies as outer-coil ownership; outer-specific void-stack and bottom-underlay passive members are allowed.
- Tx positive and negative bridge member IDs must be claimed by `type2_non_model_scene` partitioning and cannot appear in modeled body assignments.
- Void-stack ferrite/PET_PSA prefixes must resolve to passive material families without becoming copper/mesh/port ownership.
- Outer void-stack and bottom-underlay ferrite/PET_PSA prefixes must resolve to passive material families without becoming copper/mesh/port ownership.
- Outer void-stack bodies reaching the TX region top must not create active EM ports, sources, reports, boundaries, or mesh targets.
- TX inner sampled X placement tests must still fail when bounds escape `tx_inner_region`.
- TX inner actual-region validation must fail when the actual/design region is not centered in `tx_inner_region` Y or when provenance no longer matches the modeled source/physical bounds contract.

## Graph links
- Primary owner: [type2-step-import-boundary](../../../architecture/type2-step-import-boundary.md)
- Direct verification: [type2_step_import_pipeline.py](../../src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py.md)
- Direct verification: [type2_step_import_core.py](../../src/peetsfea/backend/pyaedt/type2_step_import_core.py.md)
- Related plan: [0.2.24 Type2 TX Outer Void Stack](../../../plans/0.2.24-type2-tx-outer-void-stack.md)
