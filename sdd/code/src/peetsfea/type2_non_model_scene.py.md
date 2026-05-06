---
title: type2_non_model_scene.py
created: 2026-04-28 @ 00:00
updated: 2026-05-06 @ 00:00
tags:
  - step-export
  - type2
  - rxonly
---

# type2_non_model_scene.py

## Source
- Path: `src/peetsfea/type2_non_model_scene.py`
- Code note path: `sdd/code/src/peetsfea/type2_non_model_scene.py.md`
- Status: active

## Responsibility
- Resolve and build non-modeled Type2 guide/context scene members.
- Resolve `tx_inner_region` from a parsed `tx_region.tx_reference_line` when that reference-line spec is present.
- Resolve `tx_inner_actual_region` as the non-modeled coil design outer box derived from the concrete `tx_inner_single_coil` fit-envelope placement, including selected `x_position_ratio`.
- Active Type2 export must not emit `tx_outer_region` or `tx_outer_actual_region`; those names are rejected as base non-model specs and remain absent from generated ledgers.
- During 0.2.24 TX outer removal, avoid importing the removed active `ModeledTxOuterSingleCoilSpec`; dormant outer actual-region code identifies transitional outer specs by role string only.
- Retain dormant `tx_outer_region` provenance and tilt-frame helpers for transitional callers without appending either outer guide to active Type2 scene resolution.

## Inputs / Outputs
- Inputs: non-model base specs, legacy inactive derived specs, active modeled specs needed for `tx_inner_actual_region`, deterministic seed.
- Expected parser interface: the parsed `tx_region` non-model spec is a concrete `NonModelTxRegionSpec` with a `tx_reference_line` object containing `x_ratio`, `y_usage_ratio`, and `z_ratio` `RangeSpec` fields.
- Outputs: non-modeled scene shapes and ledger entries.
- Key helpers:
  - `require_tx_outer_region_prism_provenance(object_id: Literal["tx_outer_region"]) -> TxOuterRegionPrismProvenance`
  - `resolve_tx_outer_region_tilt_frame(provenance: TxOuterRegionPrismProvenance) -> TxOuterRegionPrismTiltFrame`

## Canonical State
- `environment`, `tx_region`, and `rx_region_max` are the baseline visible non-modeled scene members.
- `tx_inner_region` is a visible non-modeled guide body resolved from `tx_region.tx_reference_line` ratios.
- `tx_inner_actual_region` is a visible non-modeled body resolved before modeled coil construction and sized to the TX inner design `outer_x_mm`/`outer_y_mm` box.
- `tx_outer_region` and `tx_outer_actual_region` are inactive remnants of the removed outer TX coil and must not appear in active generated non-model scene members.
- `tx_region_actual` and `tx_region_actual_stack_space` derived specs are inactive for RxOnly scene export.
- `tx_inner_region` reference-line ratios and resolved line endpoints are retained in a module-level provenance registry between resolution and ledger construction.
- `tx_inner_actual_region` guide bounds, design outer-box bounds, physical modeled body bounds, selected usage ratios, and modeled source id are retained in a module-level provenance registry between resolution and ledger construction.
- Dormant `resolve_tx_outer_region_tilt_frame` returns rigid local axes derived only from `TxOuterRegionPrismProvenance` semantic points when directly called by transitional code.

## Invariants / Fail-Fast
- Visible groups must resolve from required specs.
- Grouped visible geometry must form exactly one solid.
- `tx_inner_region` X/Z ratios must be finite and strictly inside `(0, 1)`, and Y usage ratio must be finite and in `(0, 1]`.
- `tx_inner_region` must derive from `tx_region`; a base box named `tx_inner_region` without reference-line provenance is rejected.
- Ledger construction for `tx_inner_region` requires matching creation-time provenance in the registry.
- `tx_inner_actual_region` requires exactly one `tx_inner_single_coil` modeled spec and must use the placement helper's design outer box so selected `outer_x_usage_ratio`/`outer_y_usage_ratio` and `x_position_ratio` are reflected exactly once. It must not use the smaller copper/PCB decomposed body bbox as canonical actual-region bounds.
- `tx_inner_actual_region.tx_actual_region.physical_modeled_body_bounds` must come from `fit_envelope.physical_modeled_body_bounds_*`, while `actual_region_bounds` remains the design outer box from `fit_envelope.design_outer_bounds_*`.
- Active resolution must not append `tx_outer_region` after `tx_inner_actual_region`.
- Base non-model specs named `tx_outer_region` or `tx_outer_actual_region` are unsupported and must raise immediately.
- Dormant `tx_outer_region` provenance accessor must reject wrong object ids and missing registry entries immediately with `RuntimeError`.
- Dormant `resolve_tx_outer_region_tilt_frame` rejects non-finite or zero-length top edges and computes a deterministic local axis triad.
- `tx_outer_actual_region` must fail fast or remain absent when no real outer TX modeled source exists; copying `tx_outer_region` as a placeholder is forbidden.
- Derived TX actual placement helpers remain fail-fast if called by unsupported paths.

## Size Note
- This file is over the 800-line split guideline. The active outer-guide removal stays in-place because it is tightly coupled to existing non-model provenance and visible group ordering; a larger split should extract all non-model guide provenance builders together.

## Collaborators
- [type2_step_export.py](type2_step_export.py.md)
- [type2_step_ledger.py](type2_step_ledger.py.md)
- [0.2.24 Type2 TX Actual Regions](../../../plans/0.2.24-type2-tx-actual-regions.md)
- [0.2.24 Type2 TX Inner Import Actual Bounds](../../../plans/0.2.24-type2-tx-inner-import-actual-bounds.md)
- [0.2.24 Type2 TX Outer Single Coil](../../../plans/0.2.24-type2-tx-outer-single-coil.md)
