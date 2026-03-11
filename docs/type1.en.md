# type1 Document

## What type1 Is
- `type1` is the baseline IPT design for TV/wall scenarios.
- TX uses `tx_dd` and `tx_vertical`, while RX uses `rx_dd`.
- Coil-group selections are normalized with PCB placement rules and then used as HFSS geometry inputs.

## What It Generates
- It generates an HFSS design file (`.aedt`).
- Zip export is currently temporarily disabled.
- These four payloads are still preserved as run snapshots:
  - `<design_id>.aedt`: HFSS design body
  - `<design_id>.repro.toml`: exact replay snapshot with all canonical sampled owners frozen
  - `<design_id>.dataset.toml`: exact sampled-coordinate ledger containing only canonical sampled owners that affect the final design (`output.*=-1`, `timeout_sec=7200`)
  - `<design_id>.source.toml`: byte-level copy of the input TOML used for the run
- `design_id` follows `seed_uniqueHash_spaceHash_attempt`. `uniqueHash` is the realized design identity, while `spaceHash` is the original `source.toml` sampling-space identity.

## Important Input Spec Blocks
- `tv`, `tx.region`, `rx.region`: scene envelope and placement anchors
- `ferrite`: global ferrite on/off plus coil-footprint-based RX/TX ferrite thickness and material defaults
- `coil_shape`, `coil_groups_params`: per-group coil geometry and derived controls
- When `tx_dd` resolves to 4 instances (two stacked XY layers), the lower layer keeps the same turn count/trace/gap but uses a one-pitch smaller centerline box so its traces interleave near the upper-layer gap centers.
- `constraints`: feasibility and topology validation rules for sampled selections
- `pcbs`: fixed-topology normalization contract. Fields normalized away from the final design must not remain independent sampled dimensions.

## Limits You Should Know
- The contract focuses on design generation; simulation-result population is out of scope.
- `manifest_<design_id>.json` and `geometry_metadata_<design_id>.json` are off by default.
- Long-term backward compatibility is not guaranteed; release contracts may change.

## Quick Checkpoints
- Input spec: `examples/type1.toml`
- Run entrypoint: `multi_sample.py` -> `build.py` or `multi_build.py`
- Default test path: run `../.venv/bin/pytest -q ../tests` from `run/`
