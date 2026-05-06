---
title: type2_step_spec_constraints.py
created: 2026-04-21 @ 20:35
updated: 2026-04-29 @ 23:59
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
- Constraint owner-path validation includes sampled `tx_region.tx_reference_line.*` owners, derived non-model owners, and modeled owners.
- Constraint owner-path validation now allows fixed modeled geometry `ModeledTvAluminumPlateSpec` without emitting sampled owner paths.

## Invariants / fail-fast
- Malformed rules, duplicate rule ids, unsupported operators, unsupported functions, and unknown owner paths must raise immediately.
- Supported function forms are loader-validated explicitly; `sum(...)` handles scalar owner arithmetic, while `tx_inner_min_trace_width_mm(tx_inner_rect_void_coil)` and `rx_min_trace_width_mm(rx_rect_void_coil)` handle type2 rect/void trace feasibility.
- Trace-width functions must name exactly one modeled object with the expected single-coil role.
- Constraint path validation only accepts paths present in the realized step spec owner-path registry.
- Modeled TV plate role has no constraint-owner fields and therefore contributes no constraint paths.

## Collaborators
- [type2_step_spec.py](type2_step_spec.py.md)
- [type2_sampled.py](type2_sampled.py.md)

## Related tests
- [test_generate_type2_step.py](../../tests/type2/test_generate_type2_step.py.md)

## Change hazards
- Keep the module free of fallback parsing paths.
- Avoid import cycles by keeping spec-model imports local where needed.
