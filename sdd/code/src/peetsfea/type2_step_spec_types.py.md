---
title: type2_step_spec_types.py
created: 2026-04-20 @ 00:00
updated: 2026-05-21 @ 00:00
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
- `NonModelTxRegionSpec` extends the regular box spec with the required TX reference-line spec and required `z_gap_from_rx_plane_mm` range owner while preserving box fields used by downstream guide paths.
- `tx_inner_single_coil` is the first geometry-only TX modeled role after the reset. It is explicit inner-coil state, not a reactivation of generic `tx_single_coil`.
- `tx_inner_single_coil` owns fixed backing stack fields for actual-region underlay repeat count, PET/PSA thickness, and ferrite thickness.
- Active single-coil modeled specs own quarter-turn public fields `x_ratio`, `y_ratio`, `turn_qcount`, `void_factor`, `metal_fill_factor`, `terminal_start`, and `void_stack_present`.
- `x_ratio` and `y_ratio` are the public placement-owner usage ratios while `outer_x_mm` and `outer_y_mm` remain derived range specs for downstream geometry handoff.
- `turn_qcount` is integer quarter-turn state. The effective full-turn count is derived by downstream geometry as `turn_qcount / 4.0`, and the allowed cap follows each role profile's `max_turn_count * 4`.
- `terminal_start` is integer corner-index state constrained to `0..3`; active type2 does not store a TOML-owned `terminal_path` on single-coil specs.
- `void_factor` replaces the old single-coil `void_usage_ratio` owner and keeps the same centered rectangular void semantics.
- `tx_inner_single_coil` and `rx_single_coil` own `void_stack_present` as the public integer switch for passive void-stack bodies; it is separate from the bottom underlay repeat owner.
- Underlay repeat count canonical sweep candidates remain `(0, 2, 4, 6, 8)`; fixed-value validation additionally accepts `1` so active TX inner examples can collapse the four thin PET/PSA/ferrite pairs into one thicker pair without changing the sampled coordinate ledger.
- Active type2 schema id remains `peetsfea.type2.step.v8`; this change extends the modeled-object selector surface without changing the top-level schema id.
- `ModeledSingleCoilCommonSpec.x_position_ratio` owns the local X placement ratio for modeled single-coil specs that still use ratio placement. The inner TX public source field `modeled_objects.tx_inner_rect_void_coil.x_position_ratio` is fixed-zero compatibility state and does not drive placement.
- Active spec/runtime unions no longer include a TX outer companion dataclass or `tx_outer_rect_void_coil` sampled owner.
- Legacy/generic TX role constants remain unsupported for active EM setup unless a later two-terminal/parallel-wiring plan enables them.
- Added modeled sheet surface `tv_aluminum_plate` (object/role `tv_aluminum_plate`) for a derived aluminum TV face sheet.
- `tv_aluminum_plate.sheet_present` is required integer `RangeSpec` state and is the spec owner for aluminum sheet presence.

## Invariants / fail-fast
- Runtime state must be concrete and non-null.
- Unsupported active role drift must fail in parser/preflight.
- TX reference-line state is never nullable; absent or invalid ratio state must fail in the parser.
- TX Z-gap state is never nullable; absent, integer, non-positive, or non-finite `z_gap_from_rx_plane_mm` ranges must fail in the parser.
- `tx_inner_single_coil` owns concrete role/object/profile identity and must not be represented as nullable or fake `tx_single_coil` state.
- X position ratio candidates must be unitless floats in the inclusive range `0.0 <= value <= 1.0`.
- Canonical underlay repeat ranges and fixed underlay repeat values are distinct constants so parser and sampling code can keep existing sweep determinism while accepting fixed one-layer coarsening.
- Canonical void-stack presence candidates are `(0, 1)` and fixed singleton values must stay in that set for TX inner and RX single-coil specs.
- Canonical terminal-start candidates are `(0, 1, 2, 3)` and fixed singleton values must stay in that set.
- Single-coil `turn_qcount` candidates must be integers in `[1, profile.max_turn_count * 4]`.
- Legacy active single-coil fields `outer_x_usage_ratio`, `outer_y_usage_ratio`, `turn_count`, `void_usage_ratio`, and `terminal_path` are unsupported schema state.
- `tv_aluminum_plate` requires fixed `object_id="tv_aluminum_plate"`, `primitive="sheet"`, `material="aluminum"`, `model_state=true`, `source_non_model_object_id="tv"`, `face="+x"`, and `thickness_mm` positive finite.
- `tv_aluminum_plate.sheet_present` must be an integer range whose realized values are only `0` and/or `1`; non-integer or out-of-domain values fail during parsing.

## Collaborators
- [type2_step_spec.py](type2_step_spec.py.md)
- [type2_step_spec_non_model.py](type2_step_spec_non_model.py.md)
- [0.2.25 Type2 Quarter-Turn Single Coil](../../../plans/0.2.25-type2-quarter-turn-single-coil.md)
- [0.2.25 Type2 TX Region Z Gap Owner](../../../plans/0.2.25-type2-tx-region-z-gap-owner.md)
- [0.2.25 Type2 TV Aluminum Sheet Presence](../../../plans/0.2.25-type2-tv-aluminum-sheet-presence.md)
- [0.2.24 Type2 TX Outer Single Coil](../../../plans/0.2.24-type2-tx-outer-single-coil.md)
- [0.2.24 Type2 TX Inner Actual Underlay Stack](../../../plans/0.2.24-type2-tx-inner-actual-underlay-stack.md)
- [0.2.24 Type2 TX Outer Void Stack](../../../plans/0.2.24-type2-tx-outer-void-stack.md)
