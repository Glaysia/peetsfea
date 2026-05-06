---
title: type2_sweep.toml
created: 2026-05-03 @ 00:00
updated: 2026-05-06 @ 00:00
tags:
  - examples
  - type2
---

# type2_sweep.toml

## Source
- Path: `examples/type2_sweep.toml`
- Code note path: `sdd/code/examples/type2_sweep.toml.md`
- Status: active example

## 역할
- Sweep-oriented type2 source TOML example for parser and sampling smoke coverage.

## Inputs / outputs
- Input: type2 parser and sampler reads this file as source TOML.
- Output: deterministic sampled owner ranges for active TX inner guide geometry and RX EM geometry.

## Canonical state
- `tx_region` is fixed non-modeled guide state; its X/Y bounds use `size_xyz[0] = 720.0`, `origin_xyz[1] = -600.0`, and `size_xyz[1] = 1200.0`.
- `non_model_objects.tx_region.tx_reference_line.x_ratio` is fixed at `[false, 0.99, 0.99, 1]` and is not an exported sampled owner.
- `non_model_objects.tx_region.tx_reference_line.y_usage_ratio` remains sampled at `[false, 0.2, 1.0, 85]`; it continues to size `tx_inner_region` inside fixed `tx_region`.
- `non_model_objects.tx_region.tx_reference_line.z_ratio` remains sampled at `[false, 0.75, 1.0, 65]`; its lower bound keeps the maximum current TX inner stack closer to the TX guide top while staying below the resolved reference line.
- `modeled_objects.tx_inner_rect_void_coil.outer_y_usage_ratio` remains sampled at `[false, 0.2, 0.9, 150]`; it continues to size the actual TX coil inside `tx_inner_region`.
- TX inner X placement source field is `modeled_objects.tx_inner_rect_void_coil.x_position_ratio` with sweep default `[false, 0.0, 0.3, 45]`.
- `modeled_objects.tx_inner_rect_void_coil` remains active with role `tx_inner_single_coil`.
- TX inner passive stack defaults are coarsened for simulation speed: `underlay_repeat_count = [true, 1, 1, 1]`, PET_PSA thickness `2.0 mm`, and ferrite thickness `2.0 mm`.
- `modeled_objects.tx_inner_rect_void_coil.void_stack_present` uses `[true, 0, 1, 2]` so sampled designs can include or omit the TX void YZ stack while keeping the bottom underlay present.
- `modeled_objects.rx_rect_void_coil` remains active with role `rx_single_coil`.
- No active example field declares `tx_outer_terminal_path` or `tx_outer_x_position_ratio`.

## Invariants / fail-fast
- Candidate values must satisfy `0.0 <= value <= 1.0`.
- TX reference-line X ratio remains parser-validated strict interior; Z ratio may reach `1.0` and must stay in `(0, 1]`.
- Active sampled owners must not include `modeled_objects.tx_outer_rect_void_coil.*`.
- Unsupported TX outer fields must be rejected by parser-level validation rather than carried as fallback state.

## Collaborators
- [type2_step_spec_modeled.py](../src/peetsfea/type2_step_spec_modeled.py.md)
- [type2_sampled_sampling.py](../src/peetsfea/type2_sampled_sampling.py.md)
- [0.2.24-type2-tx-region-y-1800-x-reference-fixed](../../plans/0.2.24-type2-tx-region-y-1800-x-reference-fixed.md)
