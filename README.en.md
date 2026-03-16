# peetsfea

peetsfea is a Python project that deterministically generates HFSS (AEDT) designs from TOML specs.  
Core principle: same spec + same seed = same result.

For Korean documentation, see [README.md](README.md).
Release notes are managed by version and language under `release-notes/`.

## Project Goals
- Standardize HFSS design generation from a single TOML spec contract.
- Preserve reproducible design generation for the same spec/version/seed.
- Keep single-design generation and dataset generation on the same contract surface.

## Current Documentation Baseline
- The current documentation baseline is `0.2.18`.
- This README is the public summary; detailed design notes live under `PLANS/`.
- For implementation rules, see [AGENTS.md](AGENTS.md). For long-term principles, see [PLANS/LONGTERM_PLAN.md](PLANS/LONGTERM_PLAN.md). [PLANS/V0_2_11.md](PLANS/V0_2_11.md) remains the archived 0.2.11 planning index.

## What This Project Intends To Guarantee
- Input: TOML spec (`examples/type1.toml`)
- Process: spec validation + deterministic selection + HFSS design generation
- Output: HFSS design output plus snapshot data (`.aedt`, `.repro.toml`, `.dataset.toml`, `.source.toml`)
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

Default execution is split across `entry/multi_sample.py` and `entry/build.py`/`entry/multi_build.py`: `entry/multi_sample.py` writes batch-specific resolved TOMLs plus manifests under `run/toml/`, and `entry/build.py` or `entry/multi_build.py` turns those manifests into AEDT files under `run/aedt/`. `entry/build_one.py` generates 100 TOMLs and builds them sequentially with the GUI visible, while `entry/sample_one_build.py` does the same for a single sample. The default runnable spec is `examples/type1.toml`.

## Core Artifacts
- Zip export is temporarily disabled.
- The run result still keeps these four payloads as snapshots:
  - `<design_id>.aedt`
  - `<design_id>.repro.toml`
  - `<design_id>.dataset.toml`
  - `<design_id>.source.toml`
- `manifest_<design_id>.json` and `geometry_metadata_<design_id>.json` are disabled by default (optional only).

## Major Contracts In 0.2.18
- Sampling ownership is managed only through canonical owners.
- Alias/derived paths do not count as independent sampled dimensions.
- `dataset.toml` includes inline sampled owners such as `coil_groups[*].count_*`, while excluding derived aliases and fixed fields.
- `dataset.toml` and `repro.toml` have different roles, and replay safety is defined by their correspondence.
- The last two `design_id` fragments have different meanings: `design_unique_hash` is the realized design identity, while `toml_space_hash` is the original `source.toml` sampling-space identity. `retry_attempt` is also reflected in the filename suffix.
- Ferrite is controlled only by the global `ferrite.present` flag, follows the actual coil footprint on both RX and TX, and uses RX `2.0mm`, TX `2.0mm`, and `mu_r=500` as the baseline spec contract.
- The TX ferrite gap is owned by the sampled path `ferrite.tx_gap_mm`, with the default example range set to `3.1..12.0`, `count=8`.
- TX ferrite must keep that gap below the lowest TX XY FR4 layer and must not touch captured TX live model objects.
- `coil_groups_params.{tx_dd,tx_vertical,rx_dd}.turn_count_max` now uses the default `2..3` range for every group, and runtime validation accepts up to `3`.
- The default runnable example now samples `tx.region.z_parts.vertical_z_mm` over `5..15`, `count=11`. Because realized `tx_vertical` height is still `min(coil_shape.tx_vertical.outer_y, tx.region.z_parts.vertical_z_mm)`, the default sample effectively uses `tx_region_vertical_z_mm` as the active height owner.
- TX DD top placement is owned by the sampled path `coil_placement.tx_dd_top_clearance_ratio`, with the default example range set to `0.0..0.3`, `count=10`. Internal `tx_dd_top_clearance_mm` is derived from `tx.region.z_parts.dd_z_mm`.
- TX vertical placement is now owned by the sampled path `coil_placement.tx_vertical_layout_mode`. `1` keeps the legacy `ZX` mode and `2` enables the new `YZ` mode.
- `coil_spacing.tx_vertical_mode2_pair_spacing_ratio` now controls the internal gap of the mode-2 RX-DD-style vertical DD pair over `0.0..0.03`, `count=25`, relative to `tx.region.outer_h_mm`. Internal `tx_vertical_mode2_pair_spacing_mm` is derived from it.
- `coil_placement.tx_vertical_mode2_x_ratio_to_tx_dd_center` now places the mode-2 RX-DD-style vertical DD pair on the RX-far `70%..100%` band of the underlying TX DD span with `count=10`. The public path name is retained, but the realized formula is `tx_dd_min_x + ratio * tx_dd_outer_x`.
- `coil_groups.tx_vertical.count_range` samples `1..6` requested coils for legacy ZX mode in the default example.
- Mode 2 still realizes exactly one DD pair per `tx_vertical` board, so larger sampled/requested counts are clamped to realized `selected_count = 1`.
- The default runnable scene now keeps the nominal `TX-region top -> RX-region bottom` gap at `50 mm` via `scene_anchor.shelf_height_mm = 461.0` under the existing scene-anchor formula.
- The public spec no longer accepts `coil_placement.tx_vertical_plane`; the realized plane is derived internally as `selected_parameters.tx_vertical_plane = "ZX" | "YZ"`.
- In mode 2 (`YZ`), the driven current orientation is fixed so that, viewed from `+X`, the right `(+Y)` half is clockwise (`-X` local B) and the left `(-Y)` half is counterclockwise (`+X` local B).
- Mode 2 (`YZ`) currently skips the legacy `Y`-side bridge no-pierce gate. That guard remains a `ZX`-only contract.
- Adaptive defaults are standardized to `percent_refinement=20`, `maximum_passes=13`, `minimum_converged_passes=10`, and `max_delta_s=0.007`.
- Detailed planning is split across the following documents:
  - [PLANS/V0_2_11.md](PLANS/V0_2_11.md)
  - [PLANS/DIVIDE_AND_CONQUER/V0_2_11_00A_SAMPLING_LEDGER_AND_PREFLIGHT.md](PLANS/DIVIDE_AND_CONQUER/V0_2_11_00A_SAMPLING_LEDGER_AND_PREFLIGHT.md)
  - [PLANS/DIVIDE_AND_CONQUER/V0_2_11_00B_SELECTION_API_SIMPLIFICATION_AND_REFACTOR.md](PLANS/DIVIDE_AND_CONQUER/V0_2_11_00B_SELECTION_API_SIMPLIFICATION_AND_REFACTOR.md)
  - [PLANS/DIVIDE_AND_CONQUER/V0_2_11_00C_REPLAY_DATASET_AND_SEEDSET_CONTRACT.md](PLANS/DIVIDE_AND_CONQUER/V0_2_11_00C_REPLAY_DATASET_AND_SEEDSET_CONTRACT.md)
  - [PLANS/DIVIDE_AND_CONQUER/V0_2_11_01_SPEC_AND_POLICY.md](PLANS/DIVIDE_AND_CONQUER/V0_2_11_01_SPEC_AND_POLICY.md)
  - [PLANS/DIVIDE_AND_CONQUER/V0_2_11_02_FERRITE_GEOMETRY_AND_METADATA.md](PLANS/DIVIDE_AND_CONQUER/V0_2_11_02_FERRITE_GEOMETRY_AND_METADATA.md)
  - [PLANS/DIVIDE_AND_CONQUER/V0_2_11_03_TESTS_AND_ACCEPTANCE.md](PLANS/DIVIDE_AND_CONQUER/V0_2_11_03_TESTS_AND_ACCEPTANCE.md)

## type1 Reference Docs
- Korean overview: [docs/type1.md](docs/type1.md)
- English overview: [docs/type1.en.md](docs/type1.en.md)

## Compatibility Policy
- Long-term backward compatibility is not guaranteed.
- Major/minor releases may change spec paths, defaults, and artifact contracts.

## Authorship & Disclaimer
- Code generation: code in this repository was generated 100% by GPT-5.x Codex.
- Liability: no warranty or liability is provided for issues arising from code/docs usage.
- English docs notice: English documents, including this README, were AI-generated and not manually reviewed. Accuracy/completeness/fitness is not guaranteed.

## Contributing
Use Issues for ideas, bug reports, and spec proposals.
