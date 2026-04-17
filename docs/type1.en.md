---
title: type1 Document
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - type1
---

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
- `ferrite`: global ferrite on/off plus coil-footprint-based RX/TX ferrite thickness and material defaults. `ferrite.tx_gap_mm` is the canonical sampled owner for the TX ferrite gap, and the default example uses `3.1..12.0` with `count=8`. TX ferrite must keep that gap below the lowest TX XY FR4 layer and remain non-contacting relative to TX coil copper, TX bridge objects, and TX FR4 live objects.
- `coil_shape`, `coil_groups_params`: per-group coil geometry and derived controls
- In the default runnable example, `tx.region.z_parts.vertical_z_mm` is sampled over `5..15`, `count=11`. Because realized `tx_vertical` height is still `min(coil_shape.neo_tx_vertical.outer_y, tx.region.z_parts.vertical_z_mm)`, the default sample effectively uses `tx_region_vertical_z_mm` as the active height owner.
- `coil_placement`: placement contracts. The default example samples `coil_placement.neo_tx_dd_top_offset_ratio` over `0.01..0.6` with `count=30`; it is the downward top-clearance ratio relative to `tx.region.z_parts.dd_z_mm`. `coil_placement.tx_vertical_orientation_mode` now means `0=no tx_vertical` and `1=ZX tx_vertical`, and the default example samples both states. `coil_groups.tx_vertical.count_range` still owns the requested ZX vertical-count dimension over `1..6`, but when orientation mode resolves to `0` the sampling owner remains recorded while realized `selected_count` becomes `0`. The public spec no longer accepts `coil_placement.tx_vertical_plane`; the realized plane remains an internal derived field and is currently fixed to `ZX`. Common geometry keys have been moved to `coil_shape.neo_tx_vertical.*` and `coil_groups_params.neo_tx_vertical.*` for the neo migration, while vertical-specific placement keys still keep the `tx_vertical_*` naming for now. `coil_placement.neo_tx_dd_right_terminal_path` and `coil_placement.neo_tx_dd_left_terminal_path` define the terminal-path contract for the right and left neo TX DD coils, and `coil_placement.neo_tx_vertical_zx_terminal_path` defines the neo TX vertical terminal-path contract for ZX/XZ coils. All values use the `<start>_<cw|ccw>_to_<end>` format, and the default example uses `B_ccw_to_c`. In no-vertical mode, the finalized TX DD objects are tilted about `Y` to satisfy the current TX-region top contract.
- When `tx_dd` resolves to 4 instances (two stacked XY layers), the lower layer keeps the same turn count/trace/gap but uses a one-pitch smaller centerline box so its traces interleave near the upper-layer gap centers.
- `constraints`: feasibility and topology validation rules for sampled selections
- `pcbs`: fixed-topology normalization contract. Fields normalized away from the final design must not remain independent sampled dimensions.

## Limits You Should Know
- The contract focuses on design generation; simulation-result population is out of scope.
- `manifest_<design_id>.json` and `geometry_metadata_<design_id>.json` are off by default.
- Long-term backward compatibility is not guaranteed; release contracts may change.

## Quick Checkpoints
- Input spec: `examples/type1.toml`
- Run entrypoint: `entry/sample.py` -> `entry/build.py`, or `entry/sample_build.py` to replay pre-generated manifests in a GUI-visible debug session
- Default test path: run `../.venv/bin/pytest -q ../tests` from `run/`
