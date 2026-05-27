---
title: type2_step_spec_constraints.py
created: 2026-04-21 @ 20:35
updated: 2026-05-27 @ 00:00
tags:
  - spec
  - constraints
---

# type2_step_spec_constraints.py

## Source
- Path: `src/peetsfea/type2_step_spec_constraints.py`
- Status: active
- Parent spec module: [type2_step_spec.py](type2_step_spec.py.md)
- Related runtime consumers: [type2_sampled.py](type2_sampled.py.md)

## Responsibility
- Own the loader-side parsing and validation helpers for active type2 `[constraints]`.
- Parse and validate declarative constraint rules from type2 step TOML.
- Validate constraint references against the realized type2 step spec owner-path set.

## Inputs / outputs
- Inputs: raw TOML tables for `[constraints]`, individual constraint rules, and a parsed `Type2StepSpec` for owner-path validation.
- Outputs: typed constraint rule objects and fail-fast validation errors.

## Canonical state
- Active operator set and constraint AST types are shared with [type2_step_spec_types.py](type2_step_spec_types.py.md).
- Active constraint rule shape requires `id`, `kind`, `message`, `enabled`, `lhs`, `op`, and `rhs`.
- Constraint operands are limited to `path`, `value`, and `func` payload tables with a single key each.
- Constraint owner-path validation includes sampled `tx_region.z_gap_from_rx_plane_mm`, `tx_region.tx_reference_line.*` owners, derived non-model owners, and modeled owners.
- Active single-coil constraint owner paths use the active quarter-turn public names `x_ratio`, `y_ratio`, `turn_qcount`, `void_factor`, `terminal_start`, and `void_stack_present`; stale public single-coil names such as `outer_x_usage_ratio`, `outer_y_usage_ratio`, `turn_count`, and `void_usage_ratio` are not admitted for those roles.
- Constraint owner-path validation includes `modeled_objects.tv_aluminum_plate.sheet_present` for the aluminum sheet presence owner.

## Invariants / fail-fast
- Malformed rules, duplicate rule ids, unsupported operators, unsupported functions, and unknown owner paths must raise immediately.
- Supported function forms are loader-validated explicitly; `sum(...)` handles scalar owner arithmetic, while `tx_inner_min_trace_width_mm(tx_inner_rect_void_coil)`, `rx_min_trace_width_mm(rx_rect_void_coil)`, and `rx_void_corridor_height_mm(rx_rect_void_coil)` handle single-coil feasibility checks.
- Trace-width functions must name exactly one modeled object with the expected single-coil role.
- Constraint path validation only accepts paths present in the realized step spec owner-path registry.
- `non_model_objects.tx_region.z_gap_from_rx_plane_mm` is a valid constraint path because it is a realized range owner in `NonModelTxRegionSpec`.
- Modeled TV aluminum sheet contributes exactly `modeled_objects.tv_aluminum_plate.sheet_present` to constraint paths.

## Collaborators
- [type2_step_spec.py](type2_step_spec.py.md)
- [type2_sampled.py](type2_sampled.py.md)
- [0.2.25 Type2 TX Region Z Gap Owner](../../../plans/0.2.25-type2-tx-region-z-gap-owner.md)
- [0.2.25 Type2 TV Aluminum Sheet Presence](../../../plans/0.2.25-type2-tv-aluminum-sheet-presence.md)

## Related tests
- [test_generate_type2_step.py](../../tests/type2/test_generate_type2_step.py.md)

## Change hazards
- Keep the module free of fallback parsing paths.
- Avoid import cycles by keeping spec-model imports local where needed.
