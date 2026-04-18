---
title: current pipeline
created: 2026-04-17 @ 15:55
updated: 2026-04-19 @ 21:20
tags:
  - type2
  - pipeline
---

# Current Pipeline

## Active Path
- The active/default product path is `type2`.
- The canonical sampled authoring input is `examples/type2_sweep.toml`.
- `examples/type2_fixed.toml` remains the fixed single-design reference.
- Type2 TOML owns both the STEP authoring registry and the EM report/output-variable contract.
- The active TX/RX plate-stack runtime boundary is documented in
  [`docs/type2-plate-stack.md`](type2-plate-stack.md).
- The active runtime flow is:
  1. `entry/sample.py`
  2. `entry/build.py`
  3. optional artifact inspection via `notebooks/hfss_sampled.ipynb`
  4. optional STEP inspection via `notebooks/view_step_files.ipynb` using `VIEW_INDEX = -1` for the fixed example or manifest entry order for sampled outputs
- `entry/sample.py` always writes `sampled.toml` and may also write STEP artifacts depending on `MAKE_STEP_ON_SAMPLE`.
- `entry/build.py` always owns `.aedt` generation and will reuse existing STEP artifacts or generate missing STEP per entry before AEDT build.
- For active plate-stack manifests, `entry/build.py` routes AEDT generation through the role-aware setup-ready facade (port-ready branch), not the import-only helper.
- If `MAKE_STEP_ON_SAMPLE = False`, sampled STEP inspection can fail until `entry/build.py` has processed that entry.

## Internal Helpers
- `peetsfea.type2_step_export` remains the STEP export helper.
- `peetsfea.backend.pyaedt.type2_step_import_pipeline` remains the import-only helper.
- `peetsfea.backend.pyaedt.type2_step_setup_ready` remains the setup-ready helper.
- `entry/build.py` always calls the setup-ready facade for active type2 build; import-only remains a geometry inspection/import-only surface.
- The setup-ready facade now handles both exact modeled pairs:
  - coil pair: full EM helper chain
  - plate-stack pair: setup-ready port-ready branch
- Plate-stack still does not own mesh/direct EM input/source/analysis/report/`ValidateDesign`.
- Direct mesh/EM helper surfaces continue to reject plate-stack roles explicitly.
- plate-stack import-only styling now reconstructs metadata-only `tx_plate_port_sheet` / `rx_plate_port_sheet`
  from ledger `stub_port` metadata; these sheets are not STEP scene bodies.
- setup-ready plate-stack branch uses the same reconstructed `tx_plate_port_sheet` / `rx_plate_port_sheet`
  with numeric boundary/excitation names `1/1_T1` and `2/2_T1`.
- plate-stack import-only styling also reconstructs ferrite-family groups as one role group each:
  `g_ferrite_tx` and `g_ferrite_rx`, with ferrite/PET_PSA/vacuum members in current creation order.
- `docs/tx-rect-void-step.md` is now the legacy coil-only geometry reference.
- These helpers are lower-level runtime surfaces; the active operator flow is sampled TOML first, then optional sample-side STEP export or build-side missing STEP export, then AEDT build.

## Legacy Path
- `type1` is frozen legacy.
- Legacy type1 code, entrypoints, examples, and tests are opt-in only:
  - `src/peetsfea/legacy/type1/`
  - `entry/legacy/type1/`
  - `tests/legacy/type1/`
  - `examples/legacy/type1.toml`
  - `docs/legacy/type1.md`
  - `docs/legacy/type1.en.md`
- The former type1 current-pipeline writeup now lives at `docs/legacy/current-pipeline-type1.md`.

## Execution Defaults
- Root/default docs, VS Code launch targets, and pytest collection should treat `type2` as the only active path.
- Legacy type1 flows must be invoked explicitly and are not part of the default acceptance surface.
