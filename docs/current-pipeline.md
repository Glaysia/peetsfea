---
title: current pipeline
created: 2026-04-17 @ 15:55
updated: 2026-04-28 @ 00:00
tags:
  - type2
  - pipeline
---

# Current Pipeline

## Active Path
- The active/default product path is `type2` RxOnly.
- The canonical sampled authoring input is `examples/type2_sweep.toml`.
- `examples/type2_fixed.toml` is one fixed realization of `examples/type2_sweep.toml` and must keep the same public field surface.
- Type2 TOML owns the STEP authoring registry and the EM report/output-variable contract.
- Public type2 range owner tables may carry `description` metadata beside `range`; official examples keep this metadata complete for every public range owner.
- Active type2 setup-ready generation uses RX modeled geometry only for EM mesh, port, source, and reports.
- `tx_inner_single_coil` may be present as geometry-only TX STEP/ledger context.
- Transmitter ports, transmitter sources, transmitter mesh ownership, and transmitter output variables are not active type2 contracts.
- `tx_region` and derived `tx_inner_region` remain non-modeled placement guide context.
- In `examples/type2_sweep.toml`, `tx_region.tx_reference_line.z_ratio` samples `[false, 0.75, 1.0, 65]` so the current maximum TX inner stack fits below the resolved reference line.
- TX inner `terminal_stub_length_mm` is TOML-owned and fixed to `7.5` mm in official type2 examples (`examples/type2_sweep.toml`, `examples/type2_fixed.toml`).
- `tv_aluminum_plate` is optional finite-conductivity HFSS sheet metadata on the source `tv` `+X` face, not a STEP solid.
- `modeled_objects.tv_aluminum_plate.sheet_present` is the canonical presence owner: the sweep example samples `[true, 0, 1, 2]`, the fixed example keeps `[true, 1, 1, 1]`, and the active sweep dimension count is 14.
- STEP export must not include a `tv_aluminum_plate` solid body. Import/setup-ready creates or skips the HFSS sheet from ledger metadata and assigns `aluminum` finite conductivity with `0.04mm` thickness only when present.
- The active runtime flow is:
  1. `entry/sample.py`
  2. `entry/build.py`
  3. optional EM solve/report export via `entry/build.py --solve`
  4. optional artifact inspection via `notebooks/hfss_sampled.ipynb`
  5. optional STEP inspection via `notebooks/view_step_files.ipynb`
- `entry/sample.py` always writes `sampled.toml` and may also write STEP artifacts depending on `MAKE_STEP_ON_SAMPLE`.
- `entry/build.py` owns `.aedt` generation and reuses existing STEP artifacts or generates missing STEP per entry before AEDT build.
- For active type2 manifests, `entry/build.py` routes AEDT generation through the setup-ready facade, not the import-only helper.
- `entry/build.py --solve` keeps the setup-ready HFSS session alive, runs `Setup1`, exports `Output Variables Table1` to CSV next to the design `.aedt`, and saves the project again.

## Runtime Helpers
- `peetsfea.type2_step_export` remains the STEP export helper.
- `peetsfea.backend.pyaedt.type2_step_import_pipeline` remains the import-only helper.
- `peetsfea.backend.pyaedt.type2_step_setup_ready` remains the setup-ready helper.
- Import-only remains a geometry inspection/import-only surface and must not create mesh, boundary, ports, reports, or setup-ready state.
- Setup-ready executes the RxOnly helper chain:
  - post-import RX conductor mesh
  - radiation boundary
  - one explicit RX lumped port
  - RX source phase
  - RX analysis/report templates
  - `validate_pipeline()`
  - `ValidateDesign()`
  - final `.aedt` save
- Active mesh ownership is RX conductor-only.
- Geometry-only TX inner bodies may be imported with the STEP scene but are not consumed by RxOnly setup-ready EM inputs.
- Reconstructed RX port-sheet geometry is runtime metadata and not a STEP body.
- Reconstructed `tv_aluminum_plate` sheet geometry is also runtime metadata and not a STEP body.
- Active report variables are the RxOnly variables documented in `sdd/architecture/type2-em-report-contract.md`.

## Legacy Path
- `type1` is frozen legacy.
- Legacy type1 code, entrypoints, examples, and tests are opt-in only:
  - `src/peetsfea/legacy/type1/`
  - `entry/legacy/type1/`
  - `tests/legacy/type1/`
  - `examples/legacy/type1.toml`
  - `docs/legacy/type1.md`
  - `docs/legacy/type1.en.md`
- Legacy coil-only rect/void reference material lives under `docs/legacy/`.

## Execution Defaults
- Root/default docs, VS Code launch targets, and pytest collection should treat `type2` RxOnly as the only active path.
- Legacy type1 flows must be invoked explicitly and are not part of the default acceptance surface.
