---
title: type2_fixed.toml
created: 2026-05-03 @ 00:00
updated: 2026-05-03 @ 00:00
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
- Output: deterministic fixed ranges and source selector tables.

## Canonical state
- TX inner X placement source field is `modeled_objects.tx_inner_rect_void_coil.x_position_ratio`.
- TX outer derived companion source selector is `modeled_objects.tx_inner_rect_void_coil.tx_outer_x_position_ratio`.
- Fixed defaults for both TX X placement selectors are `[false, 0.0, 0.0, 1]`.

## Invariants / fail-fast
- Candidate values must satisfy `0.0 <= value <= 1.0`.
- The outer selector remains under the inner TX object and maps to canonical sampled owner `modeled_objects.tx_outer_rect_void_coil.x_position_ratio`.

## Collaborators
- [type2_step_spec_modeled.py](../src/peetsfea/type2_step_spec_modeled.py.md)
- [type2_sampled.py](../src/peetsfea/type2_sampled.py.md)
