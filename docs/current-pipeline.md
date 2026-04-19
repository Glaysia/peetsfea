---
title: current pipeline
created: 2026-04-17 @ 15:55
updated: 2026-04-20 @ 00:45
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
- For active plate-stack manifests, `entry/build.py` routes AEDT generation through the role-aware setup-ready facade (full-EM-ready branch), not the import-only helper.
- If `MAKE_STEP_ON_SAMPLE = False`, sampled STEP inspection can fail until `entry/build.py` has processed that entry.

## Internal Helpers
- `peetsfea.type2_step_export` remains the STEP export helper.
- `peetsfea.backend.pyaedt.type2_step_import_pipeline` remains the import-only helper.
- `peetsfea.backend.pyaedt.type2_step_setup_ready` remains the setup-ready helper.
- `entry/build.py` always calls the setup-ready facade for active type2 build; import-only remains a geometry inspection/import-only surface.
- The setup-ready facade now handles both exact modeled pairs through the full EM helper chain:
  - post-import mesh
  - radiation boundary
  - explicit lumped ports
  - source phase
  - analysis/report
  - `validate_pipeline()`
  - `ValidateDesign()`
  - final `.aedt` save
- plate-stack mesh contract is conductor-only united copper bodies:
  - `tx_plate_copper`
  - `rx_plate_copper`
- underlay/PCB/reconstructed port-sheet bodies are not mesh targets.
- plate-stack import-only styling now reconstructs metadata-only `tx_plate_port_sheet` / `rx_plate_port_sheet`
  from ledger `stub_port` metadata; these sheets are not STEP scene bodies.
- setup-ready plate-stack branch uses the same reconstructed `tx_plate_port_sheet` / `rx_plate_port_sheet`
  with numeric boundary/excitation names `1/1_T1` and `2/2_T1`.
- active plate-stack ferrite-family STEP exact-name contract is merged-per-material, role당 3-body only:
  - TX: `tx_stack_pet_psa`, `tx_stack_ferrite`, `tx_stack_air`
  - RX: `rx_stack_pet_psa`, `rx_stack_ferrite`, `rx_stack_air`
- plate-stack ferrite-family geometry is authored as three direct equivalent slabs. `ferrite_set_count` is not a public type2 field;
  the historical 10-set baseline remains only as fixed internal thickness: PET/PSA `1.5 mm`, ferrite `2.0 mm`, air `0.2 mm`.
- plate-stack active footprint is controlled by `z_usage_ratio` and `y_usage_ratio`; Z stays role-aware
  (TX top, RX bottom), while Y is centered on global `Y=0` and fails if that centered window does not fit the owner.
- active plate-stack copper STEP exact-name contract is role-united, one conductor body per role:
  - TX: `tx_plate_copper`
  - RX: `rx_plate_copper`
- plate-stack import-only styling reconstructs copper and ferrite-family groups as role groups:
  `g_copper_tx -> [tx_plate_copper]`, `g_copper_rx -> [rx_plate_copper]`.
  `g_ferrite_tx -> [tx_stack_pet_psa, tx_stack_ferrite, tx_stack_air]`,
  `g_ferrite_rx -> [rx_stack_pet_psa, rx_stack_ferrite, rx_stack_air]`.
  `g_ferrite_tx` / `g_ferrite_rx` members는 flattened per-set stack가 아니라 위 merged 3 exact bodies다.
- import-side validation requires both role copper group and role ferrite group per role to exist in
  `expected_exported_body_groups`; any missing group or member mismatch is immediate failure before setup-ready.
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
