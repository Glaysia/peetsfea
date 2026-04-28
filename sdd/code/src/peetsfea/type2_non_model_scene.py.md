---
title: type2_non_model_scene.py
created: 2026-04-28 @ 00:00
updated: 2026-04-28 @ 12:00
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

## Inputs / Outputs
- Inputs: non-modeled base specs, legacy inactive derived specs, deterministic seed.
- Expected parser interface: the parsed `tx_region` non-model spec is a concrete `NonModelTxRegionSpec` with a `tx_reference_line` object containing `x_ratio`, `y_usage_ratio`, and `z_ratio` `RangeSpec` fields.
- Outputs: non-modeled scene shapes and ledger entries.

## Canonical State
- `environment`, `tx_region`, and `rx_region_max` are the baseline visible non-modeled scene members.
- `tx_inner_region` is a visible non-modeled guide body resolved from `tx_region.tx_reference_line` ratios.
- `tx_region_actual` and `tx_region_actual_stack_space` derived specs are inactive for RxOnly scene export.
- `tx_inner_region` reference-line ratios and resolved line endpoints are retained in a module-level provenance registry between resolution and ledger construction.

## Invariants / Fail-Fast
- Visible groups must resolve from required specs.
- Grouped visible geometry must form exactly one solid.
- `tx_inner_region` X/Z ratios must be finite and strictly inside `(0, 1)`, and Y usage ratio must be finite and in `(0, 1]`.
- `tx_inner_region` must derive from `tx_region`; a base box named `tx_inner_region` without reference-line provenance is rejected.
- Ledger construction for `tx_inner_region` requires matching creation-time provenance in the registry.
- Derived TX actual placement helpers remain fail-fast if called by unsupported paths.

## Collaborators
- [type2_step_export.py](type2_step_export.py.md)
- [type2_step_ledger.py](type2_step_ledger.py.md)
