---
title: type2_fixed.toml
created: 2026-05-03 @ 00:00
updated: 2026-05-06 @ 00:00
tags:
  - examples
  - type2
---

# type2_fixed.toml

## Source
- Path: `examples/type2_fixed.toml`
- Code note path: `sdd/code/examples/type2_fixed.toml.md`
- Status: active example

## 역할
- Fixed-value type2 source TOML example for parser and sampling smoke coverage.

## Inputs / outputs
- Input: type2 parser and sampler reads this file as source TOML.
- Output: deterministic fixed ranges for active TX inner guide geometry and RX EM geometry.

## Canonical state
- TX inner X placement source field is `modeled_objects.tx_inner_rect_void_coil.x_position_ratio`.
- `modeled_objects.tx_inner_rect_void_coil` remains active with role `tx_inner_single_coil`.
- `modeled_objects.rx_rect_void_coil` remains active with role `rx_single_coil`.
- No active example field declares `tx_outer_terminal_path` or `tx_outer_x_position_ratio`.

## Invariants / fail-fast
- Candidate values must satisfy `0.0 <= value <= 1.0`.
- Active sampled owners must not include `modeled_objects.tx_outer_rect_void_coil.*`.
- Unsupported TX outer fields must be rejected by parser-level validation rather than carried as fallback state.

## Collaborators
- [type2_step_spec_modeled.py](../src/peetsfea/type2_step_spec_modeled.py.md)
- [type2_sampled.py](../src/peetsfea/type2_sampled.py.md)
