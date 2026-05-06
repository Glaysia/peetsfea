---
title: type2_step_spec_types.py
created: 2026-04-20 @ 00:00
updated: 2026-05-06 @ 00:00
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
- `tx_inner_single_coil` is the first geometry-only TX modeled role after the reset. It is explicit inner-coil state, not a reactivation of generic `tx_single_coil`.
- `tx_inner_single_coil` owns fixed backing stack fields for actual-region underlay repeat count, PET/PSA thickness, and ferrite thickness.
- Active type2 schema id remains `peetsfea.type2.step.v8`; this change extends the modeled-object selector surface without changing the top-level schema id.
- `ModeledSingleCoilCommonSpec.x_position_ratio` owns the local X placement ratio for modeled single-coil specs. The inner TX public source field is `modeled_objects.tx_inner_rect_void_coil.x_position_ratio`.
- Active spec/runtime unions no longer include a TX outer companion dataclass or `tx_outer_rect_void_coil` sampled owner.
- Legacy/generic TX role constants remain unsupported for active EM setup unless a later two-terminal/parallel-wiring plan enables them.

## Invariants / fail-fast
- Runtime state must be concrete and non-null.
- Unsupported active role drift must fail in parser/preflight.
- TX reference-line state is never nullable; absent or invalid ratio state must fail in the parser.
- `tx_inner_single_coil` owns concrete role/object/profile identity and must not be represented as nullable or fake `tx_single_coil` state.
- X position ratio candidates must be unitless floats in the inclusive range `0.0 <= value <= 1.0`.

## Collaborators
- [type2_step_spec.py](type2_step_spec.py.md)
- [type2_step_spec_non_model.py](type2_step_spec_non_model.py.md)
- [0.2.24 Type2 TX Outer Single Coil](../../../plans/0.2.24-type2-tx-outer-single-coil.md)
- [0.2.24 Type2 TX Inner Actual Underlay Stack](../../../plans/0.2.24-type2-tx-inner-actual-underlay-stack.md)
- [0.2.24 Type2 TX Outer Void Stack](../../../plans/0.2.24-type2-tx-outer-void-stack.md)
