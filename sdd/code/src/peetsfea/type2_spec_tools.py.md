---
title: type2_spec_tools.py
created: 2026-04-29 @ 00:00
updated: 2026-05-03 @ 00:00
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
- Expose TOML-backed range owner descriptions for notebooks and external inspection tools.
- Support plain `peetsfea` installation without importing CAD/AEDT modules.

## Inputs / outputs
- Inputs: source type2 TOML paths, sampled owner value mappings, seed/sample metadata.
- Outputs: validated TOML tables, constraint tuples, owner path tuples, or rendered sampled TOML text.

## Canonical state
- Public owner values must exactly match exportable sampled owner paths.
- Rendered sampled TOML freezes owner ranges and includes deterministic sampled metadata.
- Range owner descriptions are read from TOML metadata and are not duplicated as Python hardcoded display dictionaries.
- Public owner keys remain canonical even when a canonical sampled owner is backed by a different raw TOML source field.
- The canonical owner `modeled_objects.tx_outer_rect_void_coil.x_position_ratio` is sourced from and frozen at raw TOML field `modeled_objects.tx_inner_rect_void_coil.tx_outer_x_position_ratio`; no raw `tx_outer_rect_void_coil` modeled object table is required by this helper.

## Invariants / fail-fast
- Missing or extra owner paths raise immediately.
- Missing, empty, or non-string range owner descriptions raise in the description helper.
- Missing raw TOML source fields for aliased canonical owners raise immediately with the canonical owner path and resolved source path.
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
- [test_type2_spec_tools.py](../../tests/type2/test_type2_spec_tools.py.md)
- [0.2.24-type2-range-owner-descriptions](../../../plans/0.2.24-type2-range-owner-descriptions.md)

## Change hazards
- Keep this public surface stable for surrogate/MOO workflows.
