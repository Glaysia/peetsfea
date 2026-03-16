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
- `ferrite`: global ferrite on/off plus coil-footprint-based RX/TX ferrite thickness and material defaults. `ferrite.tx_gap_mm` is the canonical sampled owner for the TX ferrite gap, and the default example uses `3.1..12.0` with `count=8`. TX ferrite must keep that gap below the lowest TX XY FR4 layer and remain non-contacting relative to TX coil copper, TX bridge objects, TX port sheet objects, and TX FR4 sheet objects.
- `coil_shape`, `coil_groups_params`: per-group coil geometry and derived controls
- `coil_placement`: placement contracts. The default example samples `coil_placement.tx_dd_top_clearance_ratio` over `0.0..0.3` with `count=10`; it is the downward top-clearance ratio relative to `tx.region.z_parts.dd_z_mm`. `coil_placement.tx_vertical_layout_mode` means `1=ZX` and `2=YZ`, and mode 2 uses `coil_spacing.tx_vertical_mode2_pair_spacing_ratio` to control the internal gap of the RX-DD-style vertical DD pair over `0.0..0.03`, `count=25`, relative to `tx.region.outer_h_mm`, while `coil_placement.tx_vertical_mode2_x_ratio_to_tx_dd_center` places that pair on the RX-far `70%..100%` band of the underlying TX DD span. The public path name is retained, but the realized formula is `tx_dd_min_x + ratio * tx_dd_outer_x`. The default example keeps `coil_groups.tx_vertical.count_range` sampled over `1..6` for legacy ZX mode, while mode 2 still realizes exactly one DD pair per `tx_vertical` board and therefore clamps the realized `selected_count` to `1`. The public spec no longer accepts `coil_placement.tx_vertical_plane`; only the realized plane remains as an internal derived field.
- In mode 2 (`YZ`), the driven current orientation is fixed so that, viewed from `+X`, the right `(+Y)` half is clockwise (`-X` local B) and the left `(-Y)` half is counterclockwise (`+X` local B).
- Mode 2 (`YZ`) currently skips the legacy `Y`-side bridge no-pierce guard. That guard remains a `ZX`-only placement contract.
- `coil_groups_params.{tx_dd,tx_vertical,rx_dd}.turn_count_max` uses the default `2..3` range for every group, and runtime validation accepts up to `3`.
- `outputs`: the SSOT for AEDT output variables and the single data-table report. The default example includes `S22_mag_ratio` and 8 WPT-derived efficiency metrics.
- `eta_*_from_*` and `eta_s21_two_sided_norm_ratio` are normalized proxy metrics, so they can become unstable when an acceptance term approaches zero.
- When `tx_dd` resolves to 4 instances (two stacked XY layers), the lower layer keeps the same turn count/trace/gap but uses a one-pitch smaller centerline box so its traces interleave near the upper-layer gap centers.
- `constraints`: feasibility and topology validation rules for sampled selections
- `pcbs`: fixed-topology normalization contract. Fields normalized away from the final design must not remain independent sampled dimensions.

## Limits You Should Know
- The contract focuses on design generation; simulation-result population is out of scope.
- `manifest_<design_id>.json` and `geometry_metadata_<design_id>.json` are off by default.
- Long-term backward compatibility is not guaranteed; release contracts may change.

## Quick Checkpoints
- Input spec: `examples/type1.toml`
- Run entrypoint: `entry/multi_sample.py` -> `entry/build.py` or `entry/multi_build.py`
- Default test path: run `../.venv/bin/pytest -q ../tests` from `run/`
