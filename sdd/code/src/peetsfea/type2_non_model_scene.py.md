---
title: type2_non_model_scene.py
created: 2026-04-28 @ 00:00
updated: 2026-04-29 @ 00:00
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
- Resolve `tx_inner_actual_region` as the non-modeled coil design outer box derived from `tx_inner_region`, `tx_inner_single_coil` sizing values, and seed.
- Resolve `tx_outer_region` as a slanted non-modeled guide prism from semantic `tx_region` and `tx_inner_region` top `+X/+Z` edges.
- Reserve `tx_outer_actual_region` for the future outer TX coil-fit envelope; it must not be emitted as a guide-region placeholder.

## Inputs / Outputs
- Inputs: non-modeled base specs, legacy inactive derived specs, modeled specs when outer TX guide height is required, deterministic seed.
- Expected parser interface: the parsed `tx_region` non-model spec is a concrete `NonModelTxRegionSpec` with a `tx_reference_line` object containing `x_ratio`, `y_usage_ratio`, and `z_ratio` `RangeSpec` fields.
- Outputs: non-modeled scene shapes and ledger entries.

## Canonical State
- `environment`, `tx_region`, and `rx_region_max` are the baseline visible non-modeled scene members.
- `tx_inner_region` is a visible non-modeled guide body resolved from `tx_region.tx_reference_line` ratios.
- `tx_inner_actual_region` is a visible non-modeled body resolved before modeled coil construction and sized to the TX inner design `outer_x_mm`/`outer_y_mm` box.
- `tx_outer_region` is a visible non-modeled guide body resolved from creation-time semantic edges, not from sorted vertices or imported geometry.
- `tx_outer_actual_region` is emitted only when a concrete outer TX modeled source exists.
- `tx_region_actual` and `tx_region_actual_stack_space` derived specs are inactive for RxOnly scene export.
- `tx_inner_region` reference-line ratios and resolved line endpoints are retained in a module-level provenance registry between resolution and ledger construction.
- `tx_inner_actual_region` guide bounds, design outer-box bounds, optional physical modeled body bounds, selected usage ratios, and modeled source id are retained in a module-level provenance registry between resolution and ledger construction.
- `tx_outer_region` vertices, resolved stack height, and source ids are retained in a module-level provenance registry between resolution, shape construction, and ledger construction.

## Invariants / Fail-Fast
- Visible groups must resolve from required specs.
- Grouped visible geometry must form exactly one solid.
- `tx_inner_region` X/Z ratios must be finite and strictly inside `(0, 1)`, and Y usage ratio must be finite and in `(0, 1]`.
- `tx_inner_region` must derive from `tx_region`; a base box named `tx_inner_region` without reference-line provenance is rejected.
- Ledger construction for `tx_inner_region` requires matching creation-time provenance in the registry.
- `tx_inner_actual_region` requires exactly one `tx_inner_single_coil` modeled spec and must use selected `outer_x_usage_ratio`/`outer_y_usage_ratio` exactly once to compute the centered design outer box. It must not use the smaller copper/PCB decomposed body bbox as canonical actual-region bounds.
- `tx_outer_region` requires exactly one `tx_inner_single_coil` modeled spec to resolve PCB thickness, layer gap, and layer count.
- `tx_outer_region` stack dimensions and resolved prism height must be finite and strictly positive.
- `tx_outer_region` top edges must come from semantic `+X/+Z` edges of `tx_region` and `tx_inner_region`; containment inside `tx_region` is not required.
- `tx_outer_actual_region` must fail fast or remain absent when no real outer TX modeled source exists; copying `tx_outer_region` as a placeholder is forbidden.
- Derived TX actual placement helpers remain fail-fast if called by unsupported paths.

## Size Note
- This file is over the 800-line split guideline. The outer guide change stays in-place because it is tightly coupled to the existing non-model provenance and visible group pipeline; a larger split should extract all non-model guide provenance builders together.

## Collaborators
- [type2_step_export.py](type2_step_export.py.md)
- [type2_step_ledger.py](type2_step_ledger.py.md)
- [0.2.24 Type2 TX Actual Regions](../../../plans/0.2.24-type2-tx-actual-regions.md)
