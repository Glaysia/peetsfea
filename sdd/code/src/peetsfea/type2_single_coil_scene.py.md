---
title: type2_single_coil_scene.py
created: 2026-04-20 @ 00:00
updated: 2026-05-07 @ 00:00
tags:
  - rx
  - scene
---

# type2_single_coil_scene.py

## Source
- Path: `src/peetsfea/type2_single_coil_scene.py`
- Code note path: `sdd/code/src/peetsfea/type2_single_coil_scene.py.md`
- Status: active

## 역할
- RX single-coil and geometry-only TX inner single-coil scene assembly helper다; dormant TX outer helper code remains outside active export.
- Expose shared owner-scaled sizing/placement helper data needed by non-model actual-region resolution, including the resolved visible physical body footprint and physical modeled body bounds.

## Invariants / fail-fast
- Invalid RX scene dimensions fail immediately.
- Invalid TX inner scene dimensions fail immediately.
- TX inner scene assembly computes mm outer ranges from the resolved `tx_inner_region` owner before building the rect-void geometry.
- TX inner scene placement is lower-X anchored: the selected physical modeled footprint min X equals `tx_inner_region` min X, Y remains centered in the owner, and top Z remains aligned to the owner top.
- Dormant TX outer scene assembly code does not import the removed active `ModeledTxOuterSingleCoilSpec` type; active export filtering prevents it from running for current Type2 generation.
- TX outer scene assembly uses a rigid tilted frame derived from `tx_outer_region_prism`: local +X follows the semantic inner-to-outer top edge, local +Y follows world +Y, and local +Z is the rotated stack normal.
- TX outer scene placement is prism-local: `x_position_ratio` is applied to the selected design outer footprint center inside the virtual sloped owner before tilt, and the virtual local owner is transformed directly into the `tx_outer_region_prism` frame with no post-rotation world-X AABB centering.
- TX inner placement and TX outer ratio placement must use their placement owner regions, not `actual_region`; actual regions are derived from the resolved visible physical footprint after placement.
- TX inner wall-side placement and TX outer ratio placement use the physical PCB/copper bbox as the visible placement reference so wall attachment and Y centering match imported AEDT geometry.
- TX inner scene placement must not read or select `spec.x_position_ratio`; the TX outer prism-local path must not change RX placement behavior.
- TX outer canonical `outer_tilt_metadata` records both accepted world +X protrusion and world -Z underhang from the rigid tilted frame.
- TX outer scene placement must read `tx_outer_region` creation-time prism provenance from the non-model scene; it must not sort or reverse-calculate the sloped prism from downstream modeled bodies.
- TX outer owner-scaled `outer_x_mm` uses the sloped top-face length.
- TX inner actual-underlay stack bodies, when requested, use `tx_inner_actual_region`/visible physical bounds as the X/Y footprint and stack in `-Z` below the actual region.
- Actual-region helpers must expose the resolved visible physical box, matching the exported modeled body bbox, so passive TX underlay/void bodies align with imported AEDT geometry.
- `RealizedSingleCoilFitEnvelope.design_outer_bounds_*` and `outer_bounds_*` are the visible physical body box intended for actual-region bounds and for TX inner wall-side placement validation.
- `RealizedSingleCoilFitEnvelope.physical_modeled_body_bounds_*` describes the same exported physical modeled body bbox used by modeled scene assembly.
- Single-coil canonical coordinates for TX single-coil modeled entries now include realized rect/void `trace_width_mm` via `fit_envelope.realized.trace_width_mm`.
  TX outer single-coil modeled entries reuse the same source from `placement.fit_envelope.realized.trace_width_mm`.
- Setup-ready mesh consumes this field to derive Length1 max length.
- The TX outer fit-envelope helper resolves the same virtual sloped owner used by `tx_outer_single_coil` scene assembly so non-model `tx_outer_actual_region` sizing cannot drift from the modeled placement path.
- `TxOuterSingleCoilScenePlacement` resolves final prism-local scene children once and returns:
  - final child geometries after tilt-frame rotation/translation,
  - final tilt rotation and frame origin used by terminal metadata,
  - final design outer AABB in world coordinates,
  - final physical modeled-body AABB and canonical bounds.
- `resolve_tx_outer_single_coil_scene_placement()` exposes `TxOuterSingleCoilScenePlacement` so non-model actual-region resolution and modeled STEP assembly share one final-placement source.
- `_build_tx_outer_single_coil_scene_data()` now consumes `TxOuterSingleCoilScenePlacement` directly; placement math is not duplicated.
- `build_modeled_single_coil_scene_data` builds `tx_inner_single_coil` underlay only when repeat_count > 0 from resolved `underlay_pet_psa_thickness_mm` and `underlay_ferrite_thickness_mm` sample values.
- `tx_inner_single_coil` underlay footprint is anchored to `fit_envelope.outer_bounds_min_xyz` and uses `fit_envelope.outer_bounds_size_xyz` in X/Y.
- `tx_inner_single_coil` underlay stacks downward from `fit_envelope.outer_bounds_min_z`: PET/PSA then MULL12060ferrite per repeat.
- `tx_inner_single_coil` emits bottom underlay from `underlay_repeat_count`; it emits the passive YZ void stack only when `void_stack_present` resolves true.
- `underlay_repeat_count = 0` suppresses only `tx_underlay_*`; it does not suppress `tx_void_*` when `void_stack_present` resolves true.
- The TX inner YZ void stack keeps realized void X bounds from `fit_envelope.realized.void_bounds`, expands Y to the copper-free central corridor associated with that void strip, spans Z from `fit_envelope.outer_bounds_min_z` to the explicit `tx_region.max_z` scene input, and uses the same nominal underlay thickness values.
- `tx_outer_single_coil` also emits a passive prism-local void stack when the derived inner repeat count is positive. The stack preserves the realized outer void prism-local X/Y footprint, is transformed by the same rotation/translation as the outer coil, and is clipped at the world-horizontal `tx_region.max_z` top boundary supplied to modeled scene assembly.
- `tx_outer_single_coil` emits a passive bottom underlay stack when the derived inner repeat count is positive. It uses the outer design/actual footprint, stacks below the outer body in local `-Z`, and is transformed by the same outer tilt frame as the coil.
- `tx_inner_single_coil` requires first PET/PSA top to align with actual-region min Z and must fail if stacked thickness exceeds `tx_inner_region` bottom; `tx_outer_single_coil` uses the same bottom-underlay ordering with outer-specific labels.
- `expected_exported_body_groups` for `tx_inner_single_coil` now includes `g_ferrite_tx` with underlay members in exported repeat order.
- `tx_outer_single_coil` terminal metadata must use the final world coordinates after outer placement: port-sheet vertices are transformed by the same world-Y tilt rotation/translation around `tilt_frame.frame_origin_xyz` used for exported scene children.
- Underlay-bearing TX single-coil, TX inner, and RX scene paths pass ordered base+underlay children through the single-coil ferrite/PET_PSA-priority boolean-clearance helper before ferrite grouping.
- The scene owns the path-specific PCB/FR4 blank labels and ferrite/PET_PSA tool labels for the helper call, while `type2_single_coil_underlay.py` owns the build123d/OCC cut implementation.
- TX outer passive void-stack and bottom-underlay ferrite/PET contracts are active for exported/imported geometry-only bodies and remain passive setup inputs.

## Contracts
- `TxOuterSingleCoilScenePlacement`:
  - `scene_children` holds the exact exported body order and labels used by TX outer modeled-step writing.
  - `design_outer_bounds_min_xyz / max_xyz / size_xyz` are world AABB bounds after prism-local x-ratio placement and full tilt.
  - `physical_modeled_body_bounds_*` are world AABB bounds and size from fully placed modeled children.
  - `physical_modeled_body_canonical_coordinates` includes canonical `outer_bounds_*` and `frame_origin_xyz` for canonical export and styling checks.
- `outer_tilt_metadata.max_world_z_underhang_mm` is derived from creation-time owner and modeled bounds; import validation may use it only for `tx_outer_single_coil`.
- `resolve_tx_outer_single_coil_scene_placement()` is the shared creation-time placement contract for both `tx_outer_actual_region` provenance and `tx_outer_single_coil` modeled output.
- `_world_aabb_from_tx_outer_prism_local_bounds` is the canonical helper for converting an axis-aligned design box in virtual outer-owner space into final prism-local world AABB.
- `_apply_single_coil_ferrite_fr4_boolean_clearance()` preserves body count, body order, and labels from the modeled scene contract; any missing helper dependency or label/order drift fails immediately.

## Collaborators
- [type2_step_scene.py](type2_step_scene.py.md)
- [0.2.24 Type2 TX Actual Regions](../../../plans/0.2.24-type2-tx-actual-regions.md)
- [0.2.24 Type2 TX Outer Single Coil](../../../plans/0.2.24-type2-tx-outer-single-coil.md)
- [0.2.24 Type2 TX Inner Actual Underlay Stack](../../../plans/0.2.24-type2-tx-inner-actual-underlay-stack.md)
- [0.2.24 Type2 TX Inner Void YZ Stack](../../../plans/0.2.24-type2-tx-inner-void-yz-stack.md)
- [0.2.24 Type2 Ferrite FR4 Boolean Clearance](../../../plans/0.2.24-type2-ferrite-fr4-boolean-clearance.md)
- [0.2.24 Type2 TX Outer Void Stack](../../../plans/0.2.24-type2-tx-outer-void-stack.md)
- [0.2.24 Type2 Trace Width Mesh Length](../../../plans/0.2.24-type2-trace-width-mesh-length.md)
