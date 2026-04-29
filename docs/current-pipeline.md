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
- Active type2 setup-ready generation uses RX modeled geometry only for EM mesh, port, source, and reports.
- `tx_inner_single_coil` may be present as geometry-only TX STEP/ledger context.
- Transmitter ports, transmitter sources, transmitter mesh ownership, and transmitter output variables are not active type2 contracts.
- `tx_region` and derived `tx_inner_region` remain non-modeled placement guide context.
- The active runtime flow is:
  1. `entry/sample.py`
  2. `entry/build.py`
  3. optional artifact inspection via `notebooks/hfss_sampled.ipynb`
  4. optional STEP inspection via `notebooks/view_step_files.ipynb`
- `entry/sample.py` always writes `sampled.toml` and may also write STEP artifacts depending on `MAKE_STEP_ON_SAMPLE`.
- `entry/build.py` owns `.aedt` generation and reuses existing STEP artifacts or generates missing STEP per entry before AEDT build.
- For active type2 manifests, `entry/build.py` routes AEDT generation through the setup-ready facade, not the import-only helper.

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
