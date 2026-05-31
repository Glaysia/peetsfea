---
title: test_type2_spec_tools.py
created: 2026-04-29 @ 00:00
updated: 2026-05-27 @ 00:00
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
- Verify generated sampled TOML excludes removed TX outer sampled owner paths.
- Verify TX inner `terminal_stub_length_mm` is TOML-owned fixed `7.5` mm in both official example manifests.
- Cover type2 constraint owner/function validation and public sample retry behavior without STEP export.
- Verify the quarter-turn single-coil sampled owner set uses `x_ratio`, `y_ratio`, `turn_qcount`, `void_factor`,
  `metal_fill_factor`, `terminal_start`, and `void_stack_present` for both TX inner and RX coils.

## Inputs / outputs
- Inputs: `examples/type2_sweep.toml`, `examples/type2_fixed.toml`, public type2 sampling APIs, public type2 spec loader, and temporary TOML copies with focused constraints.
- Outputs: pytest assertions for import surface, loadable rendered TOML, generated sampled TOML owner metadata, removed TX outer owner exclusion, fail-fast owner drift, constraint rejection, and retry metadata.

## Canonical State
- `peetsfea.type2_spec_tools` must remain usable without importing CAD/AEDT modules.
- Public sampled owner mappings must match the active exportable sampled owner set exactly, including TX inner and RX `void_stack_present` switches when sampled.
- Public sampled owner mappings must include `non_model_objects.tx_region.z_gap_from_rx_plane_mm`, sampled `tx_reference_line.y_usage_ratio` / `z_ratio`, and sampled TV sheet presence for the active sweep, bringing `examples/type2_sweep.toml` to 18 sampled dimensions.
- Constraint and retry tests use the same quarter-turn owner names as the sampled ledger; stale
  `outer_*_usage_ratio`, `turn_count`, `void_usage_ratio`, or `terminal_path` constraint paths must fail
  rather than silently aliasing to active owners.
- Official type2 examples must describe every discovered range owner path.
- Official and generated sampled TOML must carry the Korean TX inner `void_stack_present` description and freeze the sampled integer owner to `[true, value, value, 1]`.
- Generated sampled TOML must freeze sampled TV aluminum `sheet_present` to `[true, value, value, 1]` with value `0` or `1`.
- Generated sampled TOML must not include `modeled_objects.tx_outer_rect_void_coil.*` in `[sampled].sampled_owner_paths`.
- Generated sampled TOML must remain loadable and usable by the notebook-facing description helper.
- TX inner `terminal_stub_length_mm` in `examples/type2_sweep.toml` and `examples/type2_fixed.toml` must remain a fixed range with value `7.5` for deterministic ownership.
- Constraint validation must reject unknown owner paths and unsupported functions through normal TOML loading.
- Public sampling retries must happen before STEP export when constraints initially fail.

## Invariants / Fail-Fast
- Importing the lightweight tools module must not populate `build123d`, `cadquery`, or `pyaedt` in `sys.modules`.
- Missing or extra owner paths passed to `type2_sampled_toml_from_values` must raise `ValueError`.
- Missing, empty, or non-string range owner descriptions must fail through the lightweight helper.
- Description helpers must not synthesize removed TX outer owner paths.
- Notebook-equivalent coverage must generate its sampled TOML under pytest `tmp_path` and must not depend on stale local manifest artifacts.
- Invalid constraint references must raise during `load_type2_step_spec`.
- Retry coverage must use `make_step_on_sample=False` and must not require STEP/CAD export.
- Active sweep dimension audit must fail if the TX Z-gap owner drops from the exportable sampled owner set or if the sampled TV/reference-line owners drift out of the official sweep surface.
- Active sweep dimension audit must fail if any legacy single-coil owner path (`outer_x_usage_ratio`,
  `outer_y_usage_ratio`, `turn_count`, `void_usage_ratio`, or `terminal_path`) re-enters the sampled owner set.

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
- `sdd/plans/0.2.25-type2-tv-aluminum-sheet-presence.md`
- `sdd/plans/0.2.25-type2-tx-region-z-gap-owner.md`
- `sdd/plans/0.2.25-type2-quarter-turn-single-coil.md`

## Change Hazards
- Keep this module focused; do not move these assertions into existing large test files.
- If the lightweight public API signature changes intentionally, update these tests and this note together.

## Graph links
- Primary owner: [type2-spec-boundary](../../../architecture/type2-spec-boundary.md)
- Direct verification: [toml_render.py](../../src/peetsfea/spec/toml_render.py.md)
- Direct verification: [test_type2_step_spec_import_surface.py](test_type2_step_spec_import_surface.py.md)
