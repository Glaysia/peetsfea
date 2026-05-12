---
title: type2_step_export.py
created: 2026-04-28 @ 00:00
updated: 2026-05-13 @ 00:00
tags:
  - step-export
  - type2
  - rxonly
---

# type2_step_export.py

## Source
- Path: `src/peetsfea/type2_step_export.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_export.py.md`
- Status: active

## Responsibility
- Build the active Type2 STEP scene and ledger artifacts for Type2 export.
- Allow geometry-only `tx_inner_single_coil` STEP bodies while keeping derived `tx_outer_single_coil` out of the active export path.
- Pass modeled specs into non-model guide resolution so `tx_outer_region` can derive stack height from active TX inner stack parameters.
- Pass enough modeled sizing context into non-model scene resolution for `tx_inner_actual_region` to be resolved before modeled coil STEP construction.
- Reject legacy/generic modeled TX export requests with actionable errors.
- Keep dormant terminal-bridge helper code isolated from active export because active export no longer emits `tx_outer_single_coil`.
- Build terminal-bridge cross-sections from triangulated skew quads so non-coplanar terminal sheets are still manufacturable without planar-face construction.
- Record terminal-bridge material thickness metadata in the non-modeled ledger member because skew bridge canonical bboxes include span/tilt, not only physical stack thickness.
- Reuse same-call modeled scene data during post-export terminal contract validation instead of rebuilding modeled geometry a second time.
- Add modeled TV aluminum plate support as a single standalone exported body with strict no-groups/no-ports contract.
- `tx_rect_void_columns` modeled entries now carry `trace_width_mm` in `canonical_coordinates`, recovered from terminal stub anchor boxes carried through existing tile terminal metadata.
- Single-coil active Type2 terminal metadata uses the `single_coil_port_v1` runtime contract with `sheet_name`, four global-mm `vertices_xyz`, and explicit 3D integration line endpoints.
- Ledger emission records `source_toml_sha256` and `scene_step_sha256` so import can reject mixed/stale artifacts before AEDT setup proceeds.

## Inputs / Outputs
- Inputs: Type2 TOML path, output directory, ledger path, deterministic seed, optional stage reporter.
- Outputs: combined STEP scene, per-modeled-object metadata for RX bodies and geometry-only TX inner bodies, hash-bound `Type2StepLedger`.

## Canonical State
- RX modeled body names, body groups, canonical coordinates, and terminal metadata are export-owned.
- `tx_region`/`tx_inner_region` remain non-modeled guide context and placement owner context.
- `tx_outer_region` remains non-modeled guide context and follows `tx_region`/`tx_inner_region` semantic edges.
- `tx_inner_actual_region` remains non-modeled context and mirrors the TX inner coil-fit envelope without becoming the modeled coil placement owner.
- `tx_inner_single_coil` may be exported as modeled geometry, but not consumed for active TX ports, sources, or reports.
- TV aluminum plate is modeled as one body (`tv_aluminum_plate`) with `placement_owner_id = "tv"`, `plane = "YZ"`, `material = "aluminum"`, and no expected groups/ports.
- `tx_inner_single_coil` geometry and terminal metadata validation use lower-X wall-side placement inside `tx_inner_region` and centered Y placement.
- `tx_inner_single_coil` expected body validation includes actual-region bottom-underlay members in PET/PSA then ferrite order when its repeat count is positive.
- `tx_inner_single_coil` expected body validation includes generated YZ void-stack members (`tx_void_ferrite_u*` / `tx_void_pet_psa_u*`) only when `void_stack_present` resolves true.
- `tx_inner_single_coil` expected validation derives `tx_void_*` members from actual exported ledger names, then cross-checks those names against the resolved `void_stack_present` boolean.
- `tx_region.max_z` is resolved once from non-modeled scene state and passed into modeled scene construction/validation so TX inner void-stack sheets fill to the TX region top.
- `tx_outer_single_coil` specs, if still present from an in-flight loader during the removal work, are filtered out before non-model resolution, modeled scene construction, ledger creation, and terminal contract validation.
- Post-export terminal metadata validation uses the first-pass `ModeledObjectSceneData` keyed by object ID as canonical expected state for the same export call.
- Generic `tx_single_coil`, `tx_plate_stack`, and `tx_rect_void_columns` remain unsupported in active RxOnly export.
- `tx_rect_void_columns` canonical trace-width metadata is derived from each terminal anchor stub BoxSpec in `TxRectVoidColumnsTileTerminalAnchors`, enforcing consistency across all tiles/layers and requiring at least one metadata anchor to avoid fallback behavior.
- Single-coil port sheet coordinates are creation-time canonical data in `terminal_metadata.vertices_xyz`; downstream import/build code must not derive them from AEDT body bbox, sheet bbox, or terminal stub bbox.

## Invariants / Fail-Fast
- Generic modeled TX roles fail before scene construction.
- `tx_inner_single_coil` placement uses the resolved `tx_inner_region`; later code must not reverse-calculate that region from imported geometry.
- `tx_outer_region` height uses resolved modeled `tx_inner_single_coil` layer parameters and must not use literal example coordinates.
- TX inner placement validation must compare against lower-X wall-side owner anchoring, not sampled X placement, unrelated region edges, or post-hoc STEP geometry inference. Dormant TX outer placement validation keeps its owner-local ratio contract for transitional paths.
- `tx_inner_actual_region` sizing must match modeled `tx_inner_single_coil` sizing for the same seed and must not create active EM setup changes.
- `tv_aluminum_plate` requires resolved `tv` owner bounds; export fails fast if the owner or canonical dimensions are invalid before ledger emission.
- `tx_outer_actual_region`, once emitted, must match modeled `tx_outer_single_coil` sloped-owner sizing for the same seed and must not be populated from guide-only data.
- The STEP scene must keep `tx_inner_single_coil` axis-aligned while `tx_outer_single_coil` is tilted by the semantic prism frame.
- STEP export must return `True`.
- Scene body labels must be unique.
- RX terminal metadata must match the geometry contract.
- Terminal contract validation must fail if the ledger entry differs from first-pass scene data and must not call modeled geometry builders again for active single-coil entries.
- Terminal-bridge generation is inactive in active export because `tx_outer_rect_void_coil` is not present in active modeled scene data.
- Positive bridge object IDs and role remain `tx_pos_bridge_pcb`, `tx_pos_bridge_copper`, and `tx_inner_outer_positive_bridge`; its edge contract is `port_sheet_vertices_xyz[3] -> port_sheet_vertices_xyz[0]`.
- Negative bridge object IDs and role are `tx_neg_bridge_pcb`, `tx_neg_bridge_copper`, and `tx_inner_outer_negative_bridge`; its edge contract is `port_sheet_vertices_xyz[1] -> port_sheet_vertices_xyz[2]`.
- TV aluminum plate modeling has no port bridge metadata and must not enter non-model membership or bridge geometry paths.
- Terminal-bridge geometry assembly fails fast for missing terminal metadata, malformed `port_sheet_vertices_xyz`, degenerate terminal-edge geometry, non-positive dimensions, degenerate bridge triangles, or incoherent triangle normals.
- Terminal-bridge assembly requires non-degenerate start/end spans between the inner and outer terminal sheets and uses paired triangular loft operations to preserve bridge solidity on skew terminals.
- Terminal-bridge non-modeled member metadata must retain `bridge_material_thickness_mm` and `bridge_total_stack_thickness_mm`; tests must not infer those physical thicknesses from skew-shape bbox extents.
- Terminal-bridge bridge normal is derived from the bridge quad triangles' normals, and non-modeled ledger `plane` is `mixed` unless the normal is axis-aligned.
- Positive and negative bridges share the same material and thickness contract: FR4 PCB `0.365 mm`, copper `0.035 mm`, total stack `0.400 mm`.
- Single-coil terminal metadata validation fails for legacy `port_sheet_vertices_xyz`, missing `sheet_name`, malformed `vertices_xyz`, missing 3D integration line endpoints, or hash metadata that cannot bind the emitted sidecar to its source TOML and STEP scene.

## Collaborators
- [type2_step_ledger.py](type2_step_ledger.py.md)
- [type2_non_model_scene.py](type2_non_model_scene.py.md)
- [type2-em-report-contract](../../../architecture/type2-em-report-contract.md)
- [0.2.24 Type2 TX Outer Single Coil](../../../plans/0.2.24-type2-tx-outer-single-coil.md)
- [0.2.24 Type2 TX Inner Void YZ Stack](../../../plans/0.2.24-type2-tx-inner-void-yz-stack.md)
- [0.2.24 Type2 TX Outer Void Stack](../../../plans/0.2.24-type2-tx-outer-void-stack.md)
- [0.2.24 Type2 STEP Export Scene Data Reuse](../../../plans/0.2.24-type2-step-export-scene-data-reuse.md)
- [0.2.25 Type2 Port Sheet Contract Rewrite](../../../plans/0.2.25-type2-port-sheet-contract-rewrite.md)
