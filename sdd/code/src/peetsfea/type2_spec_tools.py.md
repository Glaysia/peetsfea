---
title: type2_spec_tools.py
created: 2026-04-29 @ 00:00
updated: 2026-04-29 @ 00:00
tags:
  - type2
  - spec
  - sampling
---

# type2_spec_tools.py

## Source
- Path: `src/peetsfea/type2_spec_tools.py`
- Code note path: `sdd/code/src/peetsfea/type2_spec_tools.py.md`
- Status: active

## Responsibility
- Expose lightweight type2 TOML validation, constraint extraction, sampled owner discovery, and datapoint-to-TOML rendering APIs.
- Support plain `peetsfea` installation without importing CAD/AEDT modules.

## Inputs / outputs
- Inputs: source type2 TOML paths, sampled owner value mappings, seed/sample metadata.
- Outputs: validated TOML tables, constraint tuples, owner path tuples, or rendered sampled TOML text.

## Canonical state
- Public owner values must exactly match exportable sampled owner paths.
- Rendered sampled TOML freezes owner ranges and includes deterministic sampled metadata.

## Invariants / fail-fast
- Missing or extra owner paths raise immediately.
- Constraint failures raise before TOML text is returned.
- TX inner and RX rect/void trace-width constraint functions are evaluated in pure Python.
- Generated TOML is reloaded through the lightweight validator from in-memory text before return.
- The module must not import STEP export, build123d, cadquery, pyaedt, or AEDT runtime helpers.

## Collaborators
- [type2_step_spec_constraints.py](type2_step_spec_constraints.py.md)
- [type2_step_spec_types.py](type2_step_spec_types.py.md)
- [type2_rect_void_feasibility.py](type2_rect_void_feasibility.py.md)

## Related tests
- [test_sample_type2_entry.py](../../tests/type2/test_sample_type2_entry.py.md)

## Change hazards
- Keep this public surface stable for surrogate/MOO workflows.
