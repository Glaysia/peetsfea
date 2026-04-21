---
title: type2_step_spec_constraints.py
created: 2026-04-21 @ 20:35
updated: 2026-04-21 @ 20:35
tags:
  - spec
  - constraints
---

# type2_step_spec_constraints.py

## Source
- Path: `src/peetsfea/type2_step_spec_constraints.py`
- Status: active
- Parent spec module: [[sdd/code/src/peetsfea/type2_step_spec.py]]
- Related runtime consumers: [[sdd/code/src/peetsfea/type2_sampled.py]]

## Responsibility
- Own the loader-side parsing and validation helpers for active type2 `[constraints]`.
- Parse and validate declarative constraint rules from type2 step TOML.
- Validate constraint references against the realized type2 step spec owner-path set.

## Inputs / outputs
- Inputs: raw TOML tables for `[constraints]`, individual constraint rules, and a parsed `Type2StepSpec` for owner-path validation.
- Outputs: typed constraint rule objects and fail-fast validation errors.

## Canonical state
- Active operator set and constraint AST types are shared with [[sdd/code/src/peetsfea/type2_step_spec_types.py]].
- Active constraint rule shape requires `id`, `kind`, `message`, `enabled`, `lhs`, `op`, and `rhs`.
- Constraint operands are limited to `path`, `value`, and `func` payload tables with a single key each.

## Invariants / fail-fast
- Malformed rules, duplicate rule ids, unsupported operators, unsupported functions, and unknown owner paths must raise immediately.
- `sum(...)` is the only supported constraint function form in loader parsing.
- Constraint path validation only accepts paths present in the realized step spec owner-path registry.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_sampled.py]]

## Related tests
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## Change hazards
- Keep the module free of fallback parsing paths.
- Avoid import cycles by keeping spec-model imports local where needed.
