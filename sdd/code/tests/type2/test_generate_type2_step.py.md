---
title: test_generate_type2_step.py
created: 2026-04-18 @ 09:09
updated: 2026-05-13 @ 00:00
tags:
  - test
  - step-export
---

# test_generate_type2_step.py

## Source
- Path: `tests/type2/test_generate_type2_step.py`
- Code note path: `sdd/code/tests/type2/test_generate_type2_step.py.md`
- Status: active

## 역할
- type2 STEP export and ledger contract를 검증한다.
- STEP export validation reuse tests guard against rebuilding modeled geometry during post-export terminal contract checks.
- 0.2.24 SDD 기준 RX EM geometry plus geometry-only `tx_inner_single_coil` retained under `tx_inner_region`
  are active.
- 2026-04-29 TxRx plan treats `tx_inner_single_coil` as an active EM setup target when the output mode is `TxRx`.
- Tests in this file should include TxRx-facing assertions that verify generated ledgers preserve `tx_inner_single_coil` and `rx_single_coil` modeled entries for downstream setup-ready consumption.
- Tests assert the active export omits derived `tx_outer_single_coil` modeled geometry, `tx_outer_region`, outer actual-region members, outer ferrite groups, and inner/outer bridge members while keeping TX inner and RX modeled entries active.
- Historical TX outer tilt helper tests are not active generation regressions after the 0.2.24 TX outer removal.
- Tests cover `tx_inner_actual_region` as a non-modeled coil-fit envelope derived before modeled coil construction.
- Tests cover ferrite/PET_PSA-priority boolean clearance for representative Type2 single-coil STEP export without changing exported body names, groups, or ledger contracts.
- Tests now assert the single-coil `single_coil_port_v1` contract emits global-mm `vertices_xyz`, explicit integration-line endpoints, role-specific `sheet_name`, and no legacy single-coil `port_sheet_vertices_xyz` ownership.
- Tests assert modeled ledger entries expose both semantic `canonical_coordinates` and full exported-body `exported_body_canonical_coordinates`.
- Tests assert the AEDT-facing STEP emits exact leaf body labels in `MANIFOLD_SOLID_BREP` records and does not export ferrite-family group wrappers as scene bodies.

## Canonical state
- RX exported body names/counts and terminal metadata remain deterministic.
- RX single-coil example geometry uses `pcb_thickness_mm = 3.965` and `copper_thickness_mm = 0.035`.
- RX full-backing thickness assertions derive the active coil stack thickness from exported PCB/copper bounds.
- TX inner active example geometry uses `pcb_thickness_mm = 0.3` and one-ounce `copper_thickness_mm = 0.035`.
- Fixed-example TX inner guide assertions use `tx_reference_line.z_ratio = 0.9`, so the expected `tx_inner_region` Z span is 81.0 mm.
- TX inner fixed passive defaults are `underlay_repeat_count = 1`, `underlay_pet_psa_thickness_mm = 2.0`,
  and `underlay_ferrite_thickness_mm = 2.0`; parsed example assertions should fail if those defaults drift.
- TX inner void-stack presence is controlled by `void_stack_present`; tests must cover disabled void stack while retaining bottom underlay, including the selected-size fixed example.
- The disabled export regression fixes `underlay_repeat_count = 1` and `void_stack_present = 0`; it expects `tx_underlay_*` bodies and group membership without any `tx_void_*` scene labels.
- TX inner terminal metadata remains deterministic and can drive `tx_inner_port_sheet` for `TxRx`.
- Single-coil port sheets are expected to span the facing bottom-face edges of the terminal owner boxes; diagonal-based sheet expectations are no longer active for single-coil roles.
- Fixed example parsing now asserts `tx_inner_rect_void_coil.terminal_stub_length_mm == [false, 7.5, 7.5, 1]` and `tx_inner` TX export tests assert the canonical `outer_bounds_min_xyz[2]` offset is exactly 7.5 mm above the first PCB layer `z`.
- Active `tx_inner_rect_void_coil` example and sweep contracts are single-layer: `layer_count = [true, 1, 1, 1]`.
- `tx_inner_rect_void_coil` is modeled geometry-only with expected active coil bodies `tx_inner_pcb_l0`
  and `tx_inner_copper_l0`; fixed examples also emit `tx_underlay_pet_psa_u0` and
  `tx_underlay_ferrite_u0`; it must not create `TX_TML`.
- `tx_inner_rect_void_coil` must pin owner-local visible physical min X to `tx_inner_region` min X while keeping visible physical Y centered in the owner.
- TX inner actual-underlay tests must verify only `tx_underlay_pet_psa_u0` and `tx_underlay_ferrite_u0` are emitted, share `tx_inner_actual_region` X/Y bounds, and stack downward in fixed-example 2.0 mm PET/PSA then 2.0 mm ferrite order for a 4.0 mm total bottom underlay.
- TX inner void-stack enabled tests verify generated void-stack bodies separately from the fixed example, because the selected-size fixed example disables the stack.
- TX inner ferrite-family clearance tests must verify the `g_ferrite_tx` member order remains the exported PET_PSA/ferrite underlay members, with void-stack members included only for enabled-stack cases, while every ferrite-family body and every PCB body remains a positive-volume solid.
- TX/RX ferrite group names remain ledger grouping contracts, but generated STEP labels expose only their exact leaf members for AEDT import.
- Active generation regressions must verify no `tx_outer_region`, `tx_outer_void_*`, `tx_outer_underlay_*`, `tx_outer_pcb_*`, `tx_outer_copper_*`, `tx_outer_actual_region`, `g_ferrite_tx_outer`, or TX inner/outer bridge members are emitted.
- Parser tests must reject missing, non-positive, non-fixed, and integer-flagged TX inner underlay thickness ranges.
- `tx_outer_rect_void_coil` must not appear in active modeled ledgers or STEP scene labels.
- `tx_inner_rect_void_coil` fixed-example X placement must satisfy lower-X wall-side anchoring; the physical modeled body bbox is the placement authority for imported geometry.
- TX outer X placement uses the `tx_outer_region_prism` local frame rather than post-tilt world-X AABB centering; tests validate the actual/design footprint against the prism-local center interval, including the `0.5942857142857143` regression ratio.
- `tx_outer_rect_void_coil` must be validated in the `tx_outer_region_prism` local frame. Tests derive prism-local axes and X/Y bounds from the prism provenance vertices, then assert exported body vertices remain inside those local spans.
- `examples/type2_sweep.toml` parsing must assert active TX inner and RX usage-ratio ranges, including RX inclusive `1.0` upper endpoints and shared `void_usage_ratio = [false, 0.08, 0.8, 125]`, remain parseable and scale to owner spans; it also asserts TX inner and RX `turn_count` sweep ranges are lowered to `RangeSpec(True, 1.0, 3.0, 3)`.
- `tx_outer_rect_void_coil` may protrude slightly in world +X after tilted stacking; tests should assert prism-local containment, semantic tilt, and Y/Z consistency rather than clipping to the axis-aligned prism bbox.
- `tx_outer_rect_void_coil` must preserve outer-frame tilt normals:
  each modeled outer body is validated to have a face whose normal is nearly parallel to the local normal of
  `tx_outer_region_prism.top_inner_start→top_outer_start` and whose frame `local_x` projection is non-zero.
- `tx_region` may be present as guide context only.
- Fixed examples must verify fixed non-modeled `tx_region` Y width `1800.0`, fixed `x_ratio=0.99`, preserved `y_usage_ratio`, maximum fixed TX/RX outer usage ratios, disabled TX inner void stack, fixed TX one-layer/one-turn state, and fixed RX one-turn state.
- Deterministic active tx_inner body-name contract is explicitly covered for a fixed `layer_count=1` realization:
  expected exported bodies are `tx_inner_pcb_l0` and `tx_inner_copper_l0`.
- STEP-only positive and negative inner/outer bridge geometry must be absent from active fixed-example TX paths.
- `tx_reference_line` ratio inputs, including centered `y_usage_ratio`, are expected to derive a visible non-modeled
  `tx_inner_region` STEP and retained ledger member without activating TX
  modeled geometry.
- Historical moved-`tx_region` outer-prism assertions remain with obsolete TX outer tests and must not become active generation requirements.
- `_world_terminal_stub_boxes` now resolves placement-owner specs before modeled-box rendering, and for `tx_inner_single_coil`/`tx_single_coil` it uses synthetic bus-aligned owner boxes so the world-stub geometry is validated via balanced start/end bus contract while preserving existing owner-relative semantics.
- Example mutation tests should edit parsed TOML data and re-render it instead of brittle adjacent-line string replacement, because official range owners may carry `description` metadata beside `range`.
- Active fixed-example export must not emit `tx_outer_region`; historical prism-local TX outer assertions stay xfailed with obsolete outer-modeled contracts.
- `tx_inner_actual_region` must match the resolved TX inner visible physical body box for the same TOML and seed while leaving `tx_inner_region` as the larger guide region. Its `tx_actual_region.actual_region_bounds` must equal the canonical actual-region ledger bounds, and `physical_modeled_body_bounds` must equal the modeled `tx_inner_rect_void_coil` canonical physical bounds.
- Changing TX inner `outer_x_usage_ratio` may resize `tx_inner_actual_region` and the modeled physical body, but their min X must remain equal to the unchanged `tx_inner_region` min X and their Y centers must remain equal to the owner Y center.
- `tx_outer_region` and `tx_outer_actual_region` must be absent from active fixed-example export because no active `tx_outer_rect_void_coil` exists.
- TX inner passive underlay/void-stack tests verify exported-body coordinates include passive body depth while semantic coordinates stay tied to the modeled coil/actual-region contract.

## Invariants / fail-fast
- Exported body drift and generic names fail.
- Terminal metadata drift must still fail when validation compares ledger metadata against same-call scene data.
- STEP ledger hash metadata is part of the export contract; tests that monkeypatch `export_step` must still create a STEP file so `scene_step_sha256` can be computed.
- The validation reuse regression must fail if `export_type2_step_artifacts()` calls `build_modeled_scene_data()` more times than the initial scene construction pass requires.
- The same-call scene-data drift regression mutates ledger terminal metadata after first-pass scene construction; validation must compare against the first-pass scene data and fail instead of rebuilding a second expected terminal metadata value that could mask drift.
- RxOnly EM export tests may include TX inner modeled bodies, but must not require TX terminal EM setup,
  TX outputs, or `TX_TML`.
- Generic TX modeled roles (`tx_single_coil`, `tx_rect_void_columns`, `tx_plate_stack`) remain inactive in
  active RxOnly parser/export tests; older detailed generic-TX contracts are xfailed until that mode is
  explicitly reactivated.
- TX reference-line X ratio must be strictly inside `(0, 1)`, Z and Y ratios must be in `(0, 1]`, and invalid ratios
  must fail before STEP construction.
- Historical TX outer guide/actual-region assertions are obsolete while `tx_outer_region` and `tx_outer_actual_region` remain absent from active output.
- For `tx_inner_actual_region`, the non-modeled region must carry `tx_actual_region.physical_modeled_body_bounds` that matches the final
  modeled `tx_inner_rect_void_coil` canonical bounds, while `actual_region_bounds` stays equal to the visible physical actual-region bounds.
- Active generation tests must fail if `tx_outer_rect_void_coil`, `tx_outer_region`, `tx_outer_actual_region`, or `tx_outer_*` passive/model body names return.
- TX stub contract for `tx_inner_single_coil` now requires:
  fixed-term stub span checks in helper-derived world coordinates and canonical metadata to be equal:
  no fallback to non-owner-aligned local boxes and no change in existing balanced start/end stub expectation.
- Fixed-example ledger assertions require `environment`, `tx_region`, `tx_inner_region`, `tx_inner_actual_region`,
  and `rx_region_max`; `tx_outer_region`, `tx_outer_actual_region`, and bridge members are forbidden.
- Fixed singleton `tx_reference_line.x_ratio` remains required provenance, but must not be treated as a sampled-owner dimension in sample/build tests.
- Ferrite/PET_PSA-priority clearance assertions fail if any exported ferrite-family member has positive-volume intersection with `tx_inner_pcb_l*`, if a PCB body is emptied, or if the `g_ferrite_tx` group drops/reorders members.
- STEP label assertions fail if build123d output keeps blank BREP names or if imported/round-tripped labels regress to `SOLID*`.

## Collaborators
- [generate_type2_step.py](../../entry/generate_type2_step.py.md)
- [0.2.24 Type2 TX Actual Regions](../../../plans/0.2.24-type2-tx-actual-regions.md)
- [type2_step_export.py](../../src/peetsfea/type2_step_export.py.md)
- [0.2.24-type2-tx-inner-region-non-model-step](../../../plans/0.2.24-type2-tx-inner-region-non-model-step.md)
- [0.2.24 Type2 TX Inner Actual Underlay Stack](../../../plans/0.2.24-type2-tx-inner-actual-underlay-stack.md)
- [0.2.24 Type2 TX Inner Void YZ Stack](../../../plans/0.2.24-type2-tx-inner-void-yz-stack.md)
- [0.2.24 Type2 TX Outer Void Stack](../../../plans/0.2.24-type2-tx-outer-void-stack.md)
- [0.2.24 Type2 STEP Export Scene Data Reuse](../../../plans/0.2.24-type2-step-export-scene-data-reuse.md)
- [0.2.24 Type2 Ferrite FR4 Boolean Clearance](../../../plans/0.2.24-type2-ferrite-fr4-boolean-clearance.md)
- [0.2.24-type2-tx-region-y-1800-x-reference-fixed](../../../plans/0.2.24-type2-tx-region-y-1800-x-reference-fixed.md)
- [0.2.24 Type2 Turn Count Sweep Upper Bound](../../../plans/0.2.24-type2-turn-count-sweep-upper-bound.md)
- [0.2.25 Type2 Port Sheet Contract Rewrite](../../../plans/0.2.25-type2-port-sheet-contract-rewrite.md)
- [0.2.25 Type2 Exported Body Bounds Import Validation](../../../plans/0.2.25-type2-exported-body-bounds-import-validation.md)
