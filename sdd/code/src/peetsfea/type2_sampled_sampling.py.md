---
title: type2_sampled_sampling.py
created: 2026-04-20 @ 00:00
updated: 2026-05-21 @ 00:00
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
- 0.2.25 SDD 기준 TX/RX single-coil quarter-turn sampled owners and shared constraints are active.

## 입력 / 출력
- 입력: source spec, seed, sample index, retry number
- 출력: frozen sampled values and sampled metadata

## Canonical state
- Same source spec + version + seed + retry number yields deterministic sampled values.
- TX/RX single-coil sampled owner paths use `x_ratio`, `y_ratio`, `turn_qcount`, `void_factor`, `metal_fill_factor`, `terminal_start`, and `void_stack_present`.
- Generic TX modeled roles (`tx_single_coil`, `tx_plate_stack`, `tx_rect_void_columns`) are not sampled owners.
- `tx_inner_single_coil` contributes the same seven quarter-turn sampled owners as `rx_single_coil`.
- `tv_aluminum_plate` contributes `modeled_objects.tv_aluminum_plate.sheet_present` as an integer sampled owner when its range has `count > 1`.
- TX inner `x_position_ratio` is fixed-zero compatibility state and must not appear as a sampled owner or design variable.
- Active `count > 1` range owners must appear in `sampled_owner_paths` regardless of modeled/non-modeled ownership.
- When `void_stack_present`, `turn_qcount`, or `terminal_start` use non-singleton integer ranges, they are active sampled owners and must freeze to integer singletons in sampled TOML.
- `tx_region.z_gap_from_rx_plane_mm`, `tx_region.tx_reference_line.x_ratio`, `tx_region.tx_reference_line.y_usage_ratio`, and `tx_region.tx_reference_line.z_ratio` remain discoverable non-modeled guide/context owners; official examples only sample the Z-gap because the reference-line ratios are singleton ranges.
- `tx_region_actual` and `tx_region_actual_stack_space` are not active RxOnly sampled owner sources.
- `tx_outer_single_coil` is not an active sampled modeled object. `modeled_objects.tx_outer_rect_void_coil.*` owner paths are unsupported.
- The active sweep contract is `tx_region.z_gap_from_rx_plane_mm` plus seven sampled owners per single coil, for 15 active sampled owners.

## Invariants / fail-fast
- Unknown owner paths fail immediately.
- Missing sampled-owner registration for an active non-model range is a dataset ledger bug, not a notebook display issue.
- Count>1 `tx_region.z_gap_from_rx_plane_mm` ranges must enter `sampled_owner_paths` and freeze into sampled TOML exactly like other non-modeled range owners.
- Generic TX modeled sampled owner roles fail immediately with RxOnly context.
- Any attempted sampled owner under `modeled_objects.tx_outer_rect_void_coil.*` fails.
- `tv_aluminum_plate` must expose `sheet_present` as a `RangeSpec`; missing or malformed sheet presence state fails at owner discovery.
- Fixed singleton `sheet_present` ranges stay out of sampled owner paths and sampled values.
- Constraint exhaustion is recorded only through the explicit skipped-attempt path.
- Constraint function evaluation must stay pure-Python and must not import STEP/CAD/AEDT exporters.
- Quarter-turn trace-width feasibility maps `turn_qcount` to a conservative full-turn occupancy with `ceil(turn_qcount / 4)` before calling the shared rect-void feasibility helper.
- `tx_inner_min_trace_width_mm(tx_inner_rect_void_coil)` resolves `tx_inner_region` dimensions from the sampled `tx_region.tx_reference_line.*` owners and the active retry number before applying the rect/void trace-width feasibility helper with the quarter-turn owner contract.
- `rx_min_trace_width_mm(rx_rect_void_coil)` applies the same trace-width feasibility helper against the resolved RX placement owner dimensions with the quarter-turn owner contract.
- Non-validation exceptions remain fail-fast.

## Collaborators
- [type2_sampled.py](type2_sampled.py.md)
- [type2_step_spec_sampling.py](type2_step_spec_sampling.py.md)
- [0.2.25 Type2 TX Region Z Gap Owner](../../../plans/0.2.25-type2-tx-region-z-gap-owner.md)
- [type2_rect_void_feasibility.py](type2_rect_void_feasibility.py.md)
- [0.2.24 Type2 TX Outer Single Coil](../../../plans/0.2.24-type2-tx-outer-single-coil.md)
- [0.2.25 Type2 TV Aluminum Sheet Presence](../../../plans/0.2.25-type2-tv-aluminum-sheet-presence.md)
- [0.2.25 Type2 Quarter-Turn Single Coil](../../../plans/0.2.25-type2-quarter-turn-single-coil.md)
