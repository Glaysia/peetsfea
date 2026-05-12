---
title: peetsfea
created: 2026-04-17 @ 09:09
updated: 2026-04-19 @ 15:07
tags:
  - governance
---

# peetsfea

peetsfea is a Python project that deterministically generates HFSS (AEDT) designs from TOML specs.

Core principle: same spec + same seed = same result.

For Korean documentation, see [README.md](README.md).

Release notes are managed by version and language under `release-notes/`.

## Project Goals
- Standardize HFSS design generation from a single TOML spec contract.
- Preserve reproducible design generation for the same spec/version/seed.
- Keep single-design generation and dataset generation on the same contract interface.

## Current Documentation Baseline
- The current documentation baseline is `0.2.25.1`.
- This README is the public summary. Current design notes live under `sdd/`, and active build123d/AEDT import planning lives under `PLANS/`.
- For implementation rules, see [AGENTS.md](AGENTS.md). For the current build123d/AEDT import plan, see [PLANS/V0_2_22_BUILD123D_AEDT_IMPORT_PLAN.md](PLANS/V0_2_22_BUILD123D_AEDT_IMPORT_PLAN.md).

## What This Project Intends To Guarantee
- Active input: type2 authoring spec (`examples/type2_fixed.toml`)
- Active process: type2 STEP authoring and headless HFSS import/setup-ready validation paths
- Legacy type1 paths are retained only under explicit legacy entrypoints and legacy tests/docs.
- Output: HFSS design output and snapshot data (`.aedt`, `.repro.toml`, `.dataset.toml`, `.source.toml`)
- `repro.toml`: exact replay artifact for the realized design
- `dataset.toml`: exact ledger artifact for canonical sampled-owner coordinates that affect the final design

## Quick Start
1. Prepare Python 3.12 and AEDT runtime.
2. Use the project virtual environment.
3. Run tests from `run/`.

```bash
cd run
../.venv/bin/pytest -q ../tests
```

Active default execution is type2-oriented through the type2 STEP export/import entrypoints under `entry/`. Frozen type1 batch flows are available only through explicit legacy entrypoints under `entry/legacy/type1/`.

## Development
Use the project virtual environment at `.venv`. Run repository tasks from the workspace root unless a task specifies `run/` as the working directory.

Repository runtime code under `src/` is assert-driven and fail-fast by design. Do not run the project with `python -O`; optimized mode strips required assertions and is rejected on import/runtime.

Nullable runtime state and fallback attribute/mapping access are forbidden across `src/`. Required values must be asserted and bound explicitly rather than defaulted.

`type1` is frozen legacy. The active/default surface handles only `type2`, and `type1` entry/test/doc/example files are opt-in only through legacy paths.

## Debug Launch
VS Code debug tasks in `.vscode/tasks.json` install the project in editable mode before running. This file exists so the package metadata declared in `pyproject.toml` has a valid readme target during that step.

## Core Artifacts
- Zip export is temporarily disabled.
- The run result still keeps these four payloads as snapshots:
  - `<design_id>.aedt`
  - `<design_id>.repro.toml`
  - `<design_id>.dataset.toml`
  - `<design_id>.source.toml`
- `manifest_<design_id>.json` and `geometry_metadata_<design_id>.json` are disabled by default and optional.

## Major Contracts In 0.2.25.1
- Active type2 uses a TxRx example surface with an RxOnly setup-ready backend.
- `tv_aluminum_plate` is an optional finite-conductivity HFSS sheet on the source `tv` `+X` face. It is not exported as a STEP solid.
- `modeled_objects.tv_aluminum_plate.sheet_present` is the canonical presence owner, and the active sweep dimension count is 14.
- When the sheet is present, setup-ready uses `aluminum`, `use_thickness=True`, `thickness=0.04mm`, and deterministic boundary name `bc_tv_aluminum_plate`.
- Sampling ownership is managed only through canonical owners.
- Alias/derived paths do not count as independent sampled dimensions.
- `dataset.toml` includes inline sampled owners such as `coil_groups[*].count_*`, while excluding derived aliases and fixed fields.
- `dataset.toml` and `repro.toml` have different roles, and replay safety is defined by their correspondence.
- The last two `design_id` fragments have different meanings. `design_unique_hash` is the realized design identity, while `toml_space_hash` is the original `source.toml` sampling-space identity. `retry_attempt` is also reflected in the filename suffix.
- Ferrite is controlled only by the global `ferrite.present` flag, follows the actual coil footprint on both RX and TX, and uses RX `2.0mm`, TX `2.0mm`, and `mu_r=500` as the baseline spec contract.
- The TX ferrite gap is owned by the sampled path `ferrite.tx_gap_mm`, with the default example range set to `3.1..12.0`, `count=8`.
- TX ferrite still uses `ferrite.tx_gap_mm` as the placement owner below the lowest TX XY FR4 layer, but finalized TX copper/bridge/terminal geometry is now resolved by ferrite subtract cutouts instead of a pre-subtract positive-gap rejection.
- `coil_shape.corner_mode` is the public corner-shaping owner and keeps the `0=sharp_90`, `1=blunt` contract.
- The default runnable example now samples `tx.region.z_parts.vertical_z_mm` over `5..15`, `count=11`. Because realized `tx_vertical` height is still `min(coil_shape.neo_tx_vertical.outer_y, tx.region.z_parts.vertical_z_mm)`, the default sample effectively uses `tx_region_vertical_z_mm` as the active height owner.
- TX DD top placement is owned by the sampled path `coil_placement.neo_tx_dd_top_offset_ratio`, with the default example range set to `0.01..0.6`, `count=30`. Internal `tx_dd_top_clearance_mm` is derived from `tx.region.z_parts.dd_z_mm`.
- `coil_placement.tx_vertical_orientation_mode` now means `0 = no tx_vertical` and `1 = ZX tx_vertical`.
- `coil_groups.tx_vertical.count_range` remains the canonical sampling owner for requested ZX vertical count. When orientation mode resolves to `0`, the owner still exists in the sampling ledger but realized `selected_count` becomes `0`.
- The default runnable scene now keeps the nominal `TX-region top -> RX-region bottom` gap at `50 mm` via `scene_anchor.shelf_height_mm = 461.0` under the existing scene-anchor formula.
- The public spec no longer accepts `coil_placement.tx_vertical_plane`; the realized plane is currently fixed internally as `selected_parameters.tx_vertical_plane = "ZX"`.
- When `tx_vertical_orientation_mode = 0`, the finalized TX DD conductor set is rotated about `Y` to realize the no-vertical mode while preserving the TX region top contract.
- Adaptive defaults are standardized to `percent_refinement=22`, `maximum_passes=10`, `minimum_passes=8`, `minimum_converged_passes=10`, and `max_delta_s=0.007`.
- Current detailed planning entry point: [PLANS/V0_2_22_BUILD123D_AEDT_IMPORT_PLAN.md](PLANS/V0_2_22_BUILD123D_AEDT_IMPORT_PLAN.md).

## Legacy type1 Reference Docs
- Korean overview: [docs/legacy/type1.md](docs/legacy/type1.md)
- English overview: [docs/legacy/type1.en.md](docs/legacy/type1.en.md)

## Compatibility Policy
- Long-term backward compatibility is not guaranteed.
- Major/minor releases may change spec paths, defaults, and artifact contracts.

## Release History
Release work may be squashed onto `main` to keep the public history compact. When that happens, topic branches can retain their detailed commit history, and later sync back to `main` through a normal merge once `main` has advanced again.

## Authorship & Disclaimer
- Code generation: code in this repository was generated 100% by GPT-5.x Codex.
- Liability: no warranty or liability is provided for issues arising from code/docs usage.
- English docs notice: English documents, including `README.en.md`, were AI-generated and not manually reviewed. Accuracy/completeness/fitness is not guaranteed.

## Contributing
Use Issues for ideas, bug reports, and spec proposals.
