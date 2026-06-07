---
title: ssw_step.py
created: 2026-06-07
updated: 2026-06-07
tags:
  - sdd
  - code
---

# ssw_step.py

- Path: `src/peetsfea/ssw_step.py`
- Responsibility: parse the 0.3.0 fixed SSW TOML surface, place coilmaker TX/RX coil assemblies in the TV scene, and generate CadQuery STEP geometry, action-token TOML, and a JSON ledger.
- Inputs: `examples/0.3.0_fixed.toml`, output directory, seed.
- Outputs: `coil_making_token.toml`, `ssw_scene.step`, `ssw_step_ledger.json`, and artifact metadata.
- Canonical state: fixed dimensions including the TV-to-TX spacing, TX/RX coil parameters, RX explicit SSW-vs-normal/spiral mode, `tv`, derived `tx_region`, and sweep-maximum `tx_region_max`/`rx_region_max` non-model bounds/transparency, SSW port-anchor world coordinates, scene action tokens, generated part names, body bounds, and body roles in the ledger.
- Invariants: TX and RX modeled objects must exist once, all ranges in fixed mode have `min == max` and `count == 1`, dimensions are positive, TX is always an XY-plane SSW coil inside the derived `tx_region` with its port anchor on the lower `z_min` face, RX uses a YZ-plane SSW coil with its SSW port anchor on the TV back-facing `x_min` copper face when enabled, RX may use coilmaker normal/spiral only when `is_ssw_enabled` is explicitly false, RX normal/spiral keeps quarter-turn settings in scene/action tokens, TX/RX long dimensions follow the Y axis, `tx_region` is larger than the TX coil and its top equals `TV bottom - fixed_dimensions.tx_rx_min_distance_mm`, `tx_region_max` and `rx_region_max` preserve the largest sweep-visible TX/RX coil bounds from `examples/0.3.0_sweep.toml`, token TOML is saved before STEP export, body names are unique, and CadQuery STEP export must produce a non-empty file.
- Fail-fast points: invalid TOML tables, missing parameter ranges, unfrozen fixed values, TX with SSW disabled, RX spiral quarter-turn values outside the coilmaker `0..7` and `0..3` ranges, duplicate modeled object IDs, missing `tv` or `tx_region`, unsupported roles, invalid geometry dimensions, non-transformer-ready action tokens, unparseable token TOML, and failed STEP export.
- Collaborators: [coilmaker.py](coilmaker.py.md), [debug_view_0_3_0_ssw.py](../../../entry/debug_view_0_3_0_ssw.py.md).
- Tests: [test_ssw_step.py](../../../tests/test_ssw_step.py.md).
- Change hazards: keep RX explicit normal/spiral mode separate from fallback behavior; do not rotate TX into the TV plane, move the TX port anchor off the lower face, move the RX port anchor off the TV back face in SSW mode, collapse `tx_region` into a coil-tight box, drop the sweep-maximum non-model boxes from the action/export ledger, move RX out of the TV bottom region, or add fallback minimal two-port geometry.
- Related plan: [0.3.0 ssw fixed ocp viewer](../../../plans/0.3.0-ssw-fixed-ocp-viewer.md).
