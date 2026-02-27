# peetsfea

peetsfea is a Python project that deterministically generates HFSS (AEDT) designs from TOML specs.  
Core principle: same spec + same seed = same result.

For Korean documentation, see [README.md](README.md).
Release notes are managed by version and language under `release-notes/`.

## Project-wide Goal
- Standardize HFSS design generation from a single TOML spec contract.
- Guarantee deterministic outcomes for the same spec/version/seed.
- Keep one contract that scales from single-design generation to batch runs and dataset production.

## What This Project Does
- Input: TOML spec (`examples/type1.toml`)
- Process: spec validation + parameter selection + HFSS design generation
- Output: `0.2.7` zip contract (`.aedt`, `.repro.toml`, `.dataset.toml`, `.source.toml`)

## type1 Design Overview
- `type1` is the baseline IPT design for TV/wall scenarios with TX (`tx_dd`, `tx_vertical`) and RX (`rx_dd`) coil/PCB layouts.
- Default execution produces HFSS design output plus the `0.2.7` zip artifact contract (`aedt/repro/dataset/source`).
- Required topology and constraints are pinned to `spec_version = "0.2.7"`.
- Full details: [docs/type1.en.md](docs/type1.en.md)

## Quick Start
1. Prepare Python 3.12 and AEDT runtime.
2. Use the project virtual environment.
3. Run tests from `run/`.

```bash
cd run
../.venv/bin/pytest -q ../tests
```

Default entrypoint is `run.py`, and the default runnable spec is `examples/type1.toml`.

## 0.2.7 Output Contract (Important)
- Default output unit is `<design_id>.zip`.
- Zip payload is fixed to 4 files:
  - `<design_id>.aedt`
  - `<design_id>.repro.toml`
  - `<design_id>.dataset.toml`
  - `<design_id>.source.toml`
- `manifest_<design_id>.json` and `geometry_metadata_<design_id>.json` are disabled by default (optional only).

## Compatibility Policy
- Long-term backward compatibility is not guaranteed.
- Major/minor releases may change spec paths, defaults, and artifact contracts.

## Authorship & Disclaimer
- Code generation: code in this repository was generated 100% by GPT-5.x Codex.
- Liability: no warranty or liability is provided for issues arising from code/docs usage.
- English docs notice: English documents, including this README, were AI-generated and not manually reviewed. Accuracy/completeness/fitness is not guaranteed.

## Contributing
Use Issues for ideas, bug reports, and spec proposals.
