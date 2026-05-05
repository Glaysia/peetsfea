---
title: test_type2_spec_tools.py
created: 2026-04-29 @ 00:00
updated: 2026-05-03 @ 00:00
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
- Primary graph owner: [type2-spec-boundary](../../../architecture/type2-spec-boundary.md)

## Responsibility
- Verify the lightweight `peetsfea.type2_spec_tools` import and sampled-TOML rendering API.
- Verify TOML-backed type2 range owner descriptions for official examples.
- Verify the TX outer derived owner alias reports its description from the raw TX inner selector field.
- Verify generated sampled TOML keeps the public TX outer derived owner path in sampled metadata while freezing the selected scalar on the raw TX inner source field.
- Verify TX inner `terminal_stub_length_mm` is TOML-owned fixed `7.5` mm in both official example manifests.
- Cover type2 constraint owner/function validation and public sample retry behavior without STEP export.

## Inputs / outputs
- Inputs: `examples/type2_sweep.toml`, `examples/type2_fixed.toml`, public type2 sampling APIs, public type2 spec loader, and temporary TOML copies with focused constraints.
- Outputs: pytest assertions for import surface, loadable rendered TOML, derived owner alias descriptions, generated sampled TOML owner metadata, raw source field freezing, fail-fast owner drift, constraint rejection, and retry metadata.

## Canonical State
- `peetsfea.type2_spec_tools` must remain usable without importing CAD/AEDT modules.
- Public sampled owner mappings must match the active exportable sampled owner set exactly.
- Official type2 examples must describe every discovered range owner path.
- `modeled_objects.tx_outer_rect_void_coil.x_position_ratio` is the canonical derived owner key for sampled/exported TX outer X placement, while its range and description are sourced from `modeled_objects.tx_inner_rect_void_coil.tx_outer_x_position_ratio` in TOML.
- Generated sampled TOML must preserve that derived owner key in `[sampled].sampled_owner_paths`, freeze the raw TX inner source field, remain loadable, and remain usable by the notebook-facing description helper.
- TX inner `terminal_stub_length_mm` in `examples/type2_sweep.toml` and `examples/type2_fixed.toml` must remain a fixed range with value `7.5` for deterministic ownership.
- Constraint validation must reject unknown owner paths and unsupported functions through normal TOML loading.
- Public sampling retries must happen before STEP export when constraints initially fail.

## Invariants / Fail-Fast
- Importing the lightweight tools module must not populate `build123d`, `cadquery`, or `pyaedt` in `sys.modules`.
- Missing or extra owner paths passed to `type2_sampled_toml_from_values` must raise `ValueError`.
- Missing, empty, or non-string range owner descriptions must fail through the lightweight helper.
- Derived owner descriptions must be returned under the canonical owner path, not the raw selector path, while preserving the raw selector field description text.
- Notebook-equivalent coverage must generate its sampled TOML under pytest `tmp_path` and must not depend on stale local manifest artifacts.
- Invalid constraint references must raise during `load_type2_step_spec`.
- Retry coverage must use `make_step_on_sample=False` and must not require STEP/CAD export.

## Collaborator Modules
- [type2_spec_tools.py](../../src/peetsfea/type2_spec_tools.py.md)
- [type2_sampled.py](../../src/peetsfea/type2_sampled.py.md)
- [type2_sampled_sampling.py](../../src/peetsfea/type2_sampled_sampling.py.md)
- [type2_step_spec.py](../../src/peetsfea/type2_step_spec.py.md)
- [type2_step_spec_constraints.py](../../src/peetsfea/type2_step_spec_constraints.py.md)

## Related Tests
- `tests/type2/test_sample_type2_entry.py`
- `tests/type2/test_type2_step_spec_import_surface.py`
- `sdd/plans/0.2.24-type2-range-owner-descriptions.md`

## Change Hazards
- Keep this module focused; do not move these assertions into existing large test files.
- If the lightweight public API signature changes intentionally, update these tests and this note together.

## Graph links
- Primary owner: [type2-spec-boundary](../../../architecture/type2-spec-boundary.md)
- Direct verification: [toml_render.py](../../src/peetsfea/spec/toml_render.py.md)
- Direct verification: [test_type2_step_spec_import_surface.py](test_type2_step_spec_import_surface.py.md)
