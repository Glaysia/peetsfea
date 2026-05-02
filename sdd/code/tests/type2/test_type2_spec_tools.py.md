---
title: test_type2_spec_tools.py
created: 2026-04-29 @ 00:00
updated: 2026-04-29 @ 00:00
tags:
  - test
  - type2
  - sampling
---

# test_type2_spec_tools.py

## Source
- Path: `tests/type2/test_type2_spec_tools.py`
- Code note path: `sdd/code/tests/type2/test_type2_spec_tools.py.md`
- Status: active

## Responsibility
- Verify the lightweight `peetsfea.type2_spec_tools` import and sampled-TOML rendering API.
- Verify TOML-backed type2 range owner descriptions for official examples.
- Cover type2 constraint owner/function validation and public sample retry behavior without STEP export.

## Inputs / outputs
- Inputs: `examples/type2_sweep.toml`, public type2 sampling APIs, public type2 spec loader, and temporary TOML copies with focused constraints.
- Outputs: pytest assertions for import surface, loadable rendered TOML, fail-fast owner drift, constraint rejection, and retry metadata.

## Canonical State
- `peetsfea.type2_spec_tools` must remain usable without importing CAD/AEDT modules.
- Public sampled owner mappings must match the active exportable sampled owner set exactly.
- Official type2 examples must describe every discovered range owner path.
- Constraint validation must reject unknown owner paths and unsupported functions through normal TOML loading.
- Public sampling retries must happen before STEP export when constraints initially fail.

## Invariants / Fail-Fast
- Importing the lightweight tools module must not populate `build123d`, `cadquery`, or `pyaedt` in `sys.modules`.
- Missing or extra owner paths passed to `type2_sampled_toml_from_values` must raise `ValueError`.
- Missing, empty, or non-string range owner descriptions must fail through the lightweight helper.
- Invalid constraint references must raise during `load_type2_step_spec`.
- Retry coverage must use `make_step_on_sample=False` and must not require STEP/CAD export.

## Collaborator Modules
- [type2_spec_tools.py](../../src/peetsfea/type2_spec_tools.py.md)
- [type2_sampled.py](../../src/peetsfea/type2_sampled.py.md)
- [type2_sampled_sampling.py](../../src/peetsfea/type2_sampled_sampling.py.md)
- [type2_step_spec.py](../../src/peetsfea/type2_step_spec.py.md)
- [type2_step_spec_constraints.py](../../src/peetsfea/type2_step_spec_constraints.py.md)

## Related Tests
- [test_sample_type2_entry.py](test_sample_type2_entry.py.md)
- [test_type2_step_spec_import_surface.py](test_type2_step_spec_import_surface.py.md)
- [0.2.24-type2-range-owner-descriptions](../../../plans/0.2.24-type2-range-owner-descriptions.md)

## Change Hazards
- Keep this module focused; do not move these assertions into existing large test files.
- If the lightweight public API signature changes intentionally, update these tests and this note together.
