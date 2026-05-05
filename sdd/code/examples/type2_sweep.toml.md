---
title: type2_sweep.toml
created: 2026-05-03 @ 00:00
updated: 2026-05-03 @ 00:00
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
- Output: deterministic sampled owner ranges and source selector tables.

## Canonical state
- TX inner X placement source field is `modeled_objects.tx_inner_rect_void_coil.x_position_ratio` with sweep default `[false, 0.0, 0.3, 9]`.
- TX outer derived companion source selector is `modeled_objects.tx_inner_rect_void_coil.tx_outer_x_position_ratio` with sweep default `[false, 0.0, 0.8, 36]`.
- The outer selector maps to canonical sampled owner `modeled_objects.tx_outer_rect_void_coil.x_position_ratio`.

## Invariants / fail-fast
- Candidate values must satisfy `0.0 <= value <= 1.0`.
- The derived outer companion remains source-authored through the inner TX object; the example must not add an explicit outer modeled-object TOML entry.

## Collaborators
- [type2_step_spec_modeled.py](../src/peetsfea/type2_step_spec_modeled.py.md)
- [type2_sampled_sampling.py](../src/peetsfea/type2_sampled_sampling.py.md)
