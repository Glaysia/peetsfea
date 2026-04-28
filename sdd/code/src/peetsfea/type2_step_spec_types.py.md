---
title: type2_step_spec_types.py
created: 2026-04-20 @ 00:00
updated: 2026-04-28 @ 00:00
tags:
  - spec
  - types
---

# type2_step_spec_types.py

## Source
- Path: `src/peetsfea/type2_step_spec_types.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_spec_types.py.md`
- Status: active

## 역할
- type2 spec dataclasses, constants, and helper type aliases를 소유한다.

## Inputs / outputs
- Input: parser-owned normalized values from type2 TOML.
- Output: immutable dataclasses used by parsing, sampling, scene, and export modules.

## Canonical state
- RX modeled role constants remain active.
- `tx_region` guide constants may remain as non-modeled context.
- `NonModelTxReferenceLineSpec` owns required `x_ratio`, `y_usage_ratio`, and `z_ratio` range specs for the TX reference-line anchor and centered inner Y span inside `tx_region`.
- `NonModelTxRegionSpec` extends the regular box spec with the required TX reference-line spec while preserving box fields used by downstream guide paths.
- TX shape role constants are not active SDD contracts during the 0.2.24 reset.

## Invariants / fail-fast
- Runtime state must be concrete and non-null.
- Unsupported active role drift must fail in parser/preflight.
- TX reference-line state is never nullable; absent or invalid ratio state must fail in the parser.

## Collaborators
- [type2_step_spec.py](type2_step_spec.py.md)
- [type2_step_spec_non_model.py](type2_step_spec_non_model.py.md)
