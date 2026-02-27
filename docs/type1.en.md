# type1 Document

## What type1 Is
- `type1` is the baseline IPT design for TV/wall scenarios.
- TX uses `tx_dd` and `tx_vertical`, while RX uses `rx_dd`.
- Coil-group selections are normalized with PCB placement rules and then used as HFSS geometry inputs.

## What It Generates
- It generates an HFSS design file (`.aedt`).
- It generates a `0.2.7` zip artifact.
- The zip payload is fixed to these four files:
  - `<design_id>.aedt`: HFSS design body
  - `<design_id>.repro.toml`: single-design reproducibility snapshot (`count=1`)
  - `<design_id>.dataset.toml`: dataset trace snapshot (`output.*=-1`, `timeout_sec=7200`)
  - `<design_id>.source.toml`: byte-level copy of the input TOML used for the run

## Important Input Spec Blocks
- `tv`, `tx.region`, `rx.region`: scene envelope and placement anchors
- `coil_shape`, `coil_groups_params`: per-group coil geometry and derived controls
- `constraints`: feasibility and topology validation rules for sampled selections
- `pcbs`: fixed-topology normalization contract for `0.2.7`

## Limits You Should Know
- The contract focuses on design generation; simulation-result population is out of scope.
- `manifest_<design_id>.json` and `geometry_metadata_<design_id>.json` are off by default.
- Long-term backward compatibility is not guaranteed; release contracts may change.

## Quick Checkpoints
- Input spec: `examples/type1.toml`
- Run entrypoint: `run.py`
- Default test path: run `../.venv/bin/pytest -q ../tests` from `run/`
