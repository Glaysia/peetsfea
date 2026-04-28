---
title: type2_step_spec_non_model.py
created: 2026-04-20 @ 00:00
updated: 2026-04-28 @ 00:00
tags:
  - spec
  - non-model
---

# type2_step_spec_non_model.py

## Source
- Path: `src/peetsfea/type2_step_spec_non_model.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_spec_non_model.py.md`
- Status: active

## 역할
- type2 non-model object parsing and validation helper다.

## Inputs / outputs
- Input: raw TOML tables decoded as `dict[str, object]`.
- Output: concrete non-model spec dataclasses, including `NonModelTxRegionSpec` for `tx_region`.

## Canonical state
- `tx_region` remains as future placement guide context.
- `tx_region.tx_reference_line.x_ratio` and `tx_region.tx_reference_line.z_ratio` are required `RangeSpec` owners for the TX reference-line anchor ratios.
- TX reference-line ratios remain parser/spec state only in this slice; scene/export code owns realization.
- RX region/context objects remain available to RX export/setup paths.
- Derived TX actual/stack-space shape contracts are not active SDD contracts during the reset.

## Invariants / fail-fast
- Missing required non-model context or unsupported object ids fail immediately.
- `tx_region` must contain `tx_reference_line` and that table must contain only `x_ratio` and `z_ratio`.
- TX reference-line ratio ranges must be float ranges whose realized candidates are strictly inside `(0, 1)`.
- Non-model guide objects must not create TX modeled geometry, ports, or output variables in RxOnly.

## Collaborators
- [type2_step_spec.py](type2_step_spec.py.md)
- [type2_step_spec_types.py](type2_step_spec_types.py.md)
