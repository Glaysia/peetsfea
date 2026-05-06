---
title: type2_sampled_sampling.py
created: 2026-04-20 @ 00:00
updated: 2026-05-07 @ 00:00
tags:
  - sampling
---

# type2_sampled_sampling.py

## Source
- Path: `src/peetsfea/type2_sampled_sampling.py`
- Code note path: `sdd/code/src/peetsfea/type2_sampled_sampling.py.md`
- Status: active

## 역할
- sampled owner candidate selection, retry, and freeze logic을 구현한다.
- type2 sample-time constraint evaluation을 구현한다, including `sum(...)`, `tx_inner_min_trace_width_mm(...)`, and `rx_min_trace_width_mm(...)`.
- 0.2.24 SDD 기준 RX sampled owners and shared constraints are active.

## 입력 / 출력
- 입력: source spec, seed, sample index, retry number
- 출력: frozen sampled values and sampled metadata

## Canonical state
- Same source spec + version + seed + retry number yields deterministic sampled values.
- RxOnly sampling does not require TX modeled owner values.
- Generic TX modeled roles (`tx_single_coil`, `tx_plate_stack`, `tx_rect_void_columns`) are not sampled owners.
- `tx_inner_single_coil` is a geometry-only sampled modeled owner and now contributes `void_stack_present` in addition to existing coil sizing and bottom underlay fields.
- TX inner `x_position_ratio` is fixed-zero compatibility state and must not appear as a sampled owner or design variable.
- Active `count > 1` range owners must appear in `sampled_owner_paths` regardless of modeled/non-modeled ownership.
- When `void_stack_present` uses `[true, 0, 1, 2]`, it is an active sampled owner and must freeze to an integer singleton in sampled TOML.
- `tx_region.tx_reference_line.x_ratio`, `tx_region.tx_reference_line.y_usage_ratio`, and `tx_region.tx_reference_line.z_ratio` are active non-modeled guide/context sampled owners.
- `tx_region_actual` and `tx_region_actual_stack_space` are not active RxOnly sampled owner sources.
- `tx_outer_single_coil` is not an active sampled modeled object. `modeled_objects.tx_outer_rect_void_coil.*` owner paths are unsupported.

## Invariants / fail-fast
- Unknown owner paths fail immediately.
- Missing sampled-owner registration for an active non-model range is a dataset ledger bug, not a notebook display issue.
- Generic TX modeled sampled owner roles fail immediately with RxOnly context.
- Any attempted sampled owner under `modeled_objects.tx_outer_rect_void_coil.*` fails.
- Constraint exhaustion is recorded only through the explicit skipped-attempt path.
- Constraint function evaluation must stay pure-Python and must not import STEP/CAD/AEDT exporters.
- `tx_inner_min_trace_width_mm(tx_inner_rect_void_coil)` resolves `tx_inner_region` dimensions from the sampled `tx_region.tx_reference_line.*` owners and the active retry number before applying the rect/void trace-width feasibility helper.
- `rx_min_trace_width_mm(rx_rect_void_coil)` applies the same trace-width feasibility helper against the resolved RX placement owner dimensions.
- Non-validation exceptions remain fail-fast.

## Collaborators
- [type2_sampled.py](type2_sampled.py.md)
- [type2_step_spec_sampling.py](type2_step_spec_sampling.py.md)
- [type2_rect_void_feasibility.py](type2_rect_void_feasibility.py.md)
- [0.2.24 Type2 TX Outer Single Coil](../../../plans/0.2.24-type2-tx-outer-single-coil.md)
