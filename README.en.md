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
- The current documentation baseline is `0.2.12`.
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

Default execution is split across `sample.py` and `build.py`: `sample.py` writes resolved TOMLs plus `run/toml/manifest.json`, and `build.py` turns that manifest into AEDT files under `run/aedt/`. The default runnable spec is `examples/type1.toml`.

## Core Artifacts
- Zip export is temporarily disabled.
- The run result still keeps these four payloads as snapshots:
  - `<design_id>.aedt`
  - `<design_id>.repro.toml`
  - `<design_id>.dataset.toml`
  - `<design_id>.source.toml`
- `manifest_<design_id>.json` and `geometry_metadata_<design_id>.json` are disabled by default (optional only).

## Major Contracts In 0.2.12
- Sampling ownership is managed only through canonical owners.
- Alias/derived paths do not count as independent sampled dimensions.
- `dataset.toml` includes inline sampled owners such as `coil_groups[*].count_*`, while excluding derived aliases and fixed fields.
- `dataset.toml` and `repro.toml` have different roles, and replay safety is defined by their correspondence.
- The last two `design_id` fragments have different meanings: `design_unique_hash` is the realized design identity, while `toml_space_hash` is the original `source.toml` sampling-space identity. `retry_attempt` is also reflected in the filename suffix.
- Ferrite is controlled only by the global `ferrite.present` flag, follows the actual coil footprint on both RX and TX, and uses RX `2.0mm`, TX `2.0mm`, and `mu_r=500` as the baseline spec contract.
- Adaptive defaults are standardized to `percent_refinement=20`, `maximum_passes=20`, and `max_delta_s=0.007`.
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
