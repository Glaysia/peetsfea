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
- TX inner X placement source field is `modeled_objects.tx_inner_rect_void_coil.x_position_ratio` with sweep default `[false, 0.0, 0.3, 9]`.
- `modeled_objects.tx_inner_rect_void_coil` remains active with role `tx_inner_single_coil`.
- TX inner passive stack defaults are coarsened for simulation speed: `underlay_repeat_count = [true, 1, 1, 1]`, PET_PSA thickness `2.0 mm`, and ferrite thickness `2.0 mm`.
- `modeled_objects.rx_rect_void_coil` remains active with role `rx_single_coil`.
- No active example field declares `tx_outer_terminal_path` or `tx_outer_x_position_ratio`.

## Invariants / fail-fast
- Candidate values must satisfy `0.0 <= value <= 1.0`.
- Active sampled owners must not include `modeled_objects.tx_outer_rect_void_coil.*`.
- Unsupported TX outer fields must be rejected by parser-level validation rather than carried as fallback state.

## Collaborators
- [type2_step_spec_modeled.py](../src/peetsfea/type2_step_spec_modeled.py.md)
- [type2_sampled_sampling.py](../src/peetsfea/type2_sampled_sampling.py.md)
