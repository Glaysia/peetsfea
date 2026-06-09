---
title: ssw_step_constraints.py
created: 2026-06-08
updated: 2026-06-10
tags:
  - sdd
  - code
  - constraints
---

# ssw_step_constraints.py

- Path: `src/peetsfea/ssw_step_constraints.py`
- Responsibility: parse and evaluate the 0.3.0 SSW `[constraints]` TOML rules before geometry generation.
- Inputs: raw TOML root tables, parsed TX/RX coil constraint values, and declarative comparison rules.
- Outputs: typed SSW constraint rules or fail-fast validation errors with rule id, message, operands, and operator.
- Canonical state: `constraints.rules`, rule ids, comparison operands, function expressions, and per-coil SSW connectivity values.
- Invariants: every rule has `id`, `kind`, `message`, `enabled`, `lhs`, `op`, and `rhs`; supported operands are exactly `{path=...}`, `{value=...}`, and `{func=...}`; supported function calls are limited to `ssw_conductor_component_count(object_id)`; SSW-enabled coils must evaluate to one conductor component, and RX SSW must have `turn_n_int > 1` when enabled, to pass the public example constraints.
- Fail-fast points: missing constraints table, malformed rule table, duplicate rule id, unsupported function/operator, unknown path/object id, non-numeric ordered comparison, and failed comparison.
- Collaborators: [ssw_step.py](ssw_step.py.md).
- Tests: [test_ssw_step.py](../../../tests/test_ssw_step.py.md).
- Change hazards: do not add expression fallback behavior, do not skip enabled or malformed rules, and keep the TOML shape aligned with the 0.2.25 type2 `[[constraints.rules]]` public surface.
