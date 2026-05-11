---
title: test_type2_step_import_pipeline.py
created: 2026-04-18 @ 09:09
updated: 2026-05-11 @ 00:00
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
- `tx_outer_single_coil` source ledgers are rejected as inactive Type2 state before import/styling.

## Canonical state
- Import ledger preserves source paths, seed, imported ownership, and imported object names.
- Import ledger preserves modeled canonical `trace_width_mm` so setup-ready mesh can derive dynamic `Length1.MaxLength`.
- Import-only path must not create boundary, ports, mesh, or reports.
- `tx_region` may be carried as guide context only.
- Geometry-only `tx_inner_single_coil` import partition accepts an empty body-group contract.
- `tx_inner_single_coil` actual-underlay fixtures require `g_ferrite_tx` member order to match export order: `tx_underlay_pet_psa_u*` before `tx_underlay_ferrite_u*`.
- `tx_inner_single_coil` void-stack fixtures require `g_ferrite_tx` member order to include `tx_void_ferrite_u*` and `tx_void_pet_psa_u*` exactly as export declares them.
- Disabled `tx_inner_single_coil` void-stack fixtures require `g_ferrite_tx` to accept underlay-only membership while `tx_void_*` bodies are absent from expected, imported, and styled names.
- Enabled `tx_inner_single_coil` void-stack fixtures require `g_ferrite_tx` member order to include bottom underlay members plus exactly the computed void pair members export declares.
- Active fixed/sweep import fixtures treat TX inner as layer-count one and must not expect `tx_inner_copper_stack`.
- STEP ledger load coverage verifies the same TX inner void-stack group contract before PyAEDT import begins.
- TX inner underlay import fixtures include the non-modeled `tx_inner_region` owner and `tx_inner_actual_region` provenance before import-bound validation runs.
- TX inner actual-region regression coverage preserves a large guide owner with a lower-X wall-side anchored design/actual region, Y centering, and matching physical modeled bbox provenance.
- TX inner import/style coverage must preserve enabled `tx_void_*` passive bodies and accept disabled void-stack ledgers that still include bottom `tx_underlay_*` bodies.
- TX inner import fixtures include the derived non-modeled `tx_inner_actual_region` member with `tx_actual_region` provenance whenever `tx_inner_single_coil` validation requires the design/actual bounds contract.
- `tx_inner_single_coil` bounds coverage accepts lower-X wall-side X placement inside `tx_inner_region` while requiring physical modeled bounds provenance to match the modeled ledger entry.
- TX inner actual-region regression coverage accepts centered design bounds at Y `[-84, 84]` when the recorded physical modeled bounds are smaller and asymmetric, such as `min_y=-84.0` and `size_y=164.07134831460672`.
- Ledger fixtures declare `outputs.mode = "RxOnly"` and only active RX output variables.
- Tests preserve a fail-fast regression that any fixture declaring `tx_outer_single_coil` is unsupported.
- Tx terminal bridge members are allowed as non-model scene members (`tx_pos_bridge_pcb`, `tx_pos_bridge_copper`, `tx_neg_bridge_pcb`, `tx_neg_bridge_copper`) and must stay in non-modeled buckets.
- TV aluminum plate modeled import coverage requires modeled ledger entries with role/object_id `tv_aluminum_plate`, placement owner `tv`, canonical min/size contract, and import-time `imported_object_names` behavior.
- The tv aluminum plate import regression is active and must pass without xfail: backend ledger, partition, bounds, styling, and imported ledger output all recognize the modeled one-body aluminum plate.
- Single-coil and `tx_rect_void_columns` modeled fixtures now include positive canonical `trace_width_mm` and import tests assert source-to-imported preservation.
- Plate-stack modeled fixtures set positive canonical `trace_width_mm` (stripe-derived) and import tests assert preservation on canonical-coordinate round-trip.
- Shared mesh payload fixtures expect `Length1` with `RestrictElem=True`, `NumMaxElem=24000`, `RestrictLength=True`, and the documented max-length value for their fixture shape.

## Invariants / fail-fast
- Missing RX imported bodies and generic imported names fail.
- RxOnly import tests must not require TX modeled bodies.
- Tx bridge member IDs must be claimed by `type2_non_model_scene` partitioning and cannot appear in modeled body assignments.
- Tx positive and negative bridge member IDs must be claimed by `type2_non_model_scene` partitioning and cannot appear in modeled body assignments.
- Void-stack ferrite/PET_PSA prefixes must resolve to passive material families (`MULL12060ferrite` for ferrite and `PET_PSA` for PET/PSA) without becoming copper/mesh/port ownership.
- TX inner wall-side X placement tests must still fail when bounds escape `tx_inner_region` or when actual-region provenance no longer anchors at the lower-X owner side.
- TX inner actual-region validation must fail when the actual/design region is not centered in `tx_inner_region` Y or when provenance no longer matches the modeled source/physical bounds contract.
- tv aluminum plate modeled import assertions require non-modeled member `tv` to remain available as the placement owner while `tv_aluminum_plate` stays out of non-modeled ownership.
- Imported `trace_width_mm` for single-coil, `tx_rect_void_columns`, and plate-stack entries is verified before and after import.
- Modeled fixtures that participate in setup-ready mesh include positive canonical trace width metadata.

## Graph links
- Primary owner: [type2-step-import-boundary](../../../architecture/type2-step-import-boundary.md)
- Direct verification: [type2_step_import_pipeline.py](../../src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py.md)
- Direct verification: [type2_step_import_core.py](../../src/peetsfea/backend/pyaedt/type2_step_import_core.py.md)
- Related plan: [0.2.24 Type2 TX Outer Void Stack](../../../plans/0.2.24-type2-tx-outer-void-stack.md)
- Related plan: [0.2.24 Type2 TV Aluminum Plate](../../../plans/0.2.24-type2-tv-aluminum-plate.md)
- Related plan: [0.2.24 Type2 Trace Width Mesh Length](../../../plans/0.2.24-type2-trace-width-mesh-length.md)
