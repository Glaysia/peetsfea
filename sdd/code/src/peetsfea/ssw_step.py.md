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
- Responsibility: parse the 0.3.0 fixed SSW TOML surface, place coilmaker TX/RX coil assemblies and MULL ferrite sheets in the TV scene, and generate CadQuery STEP geometry, action-token TOML, and a JSON ledger.
- Inputs: `examples/0.3.0_fixed.toml`, output directory, seed.
- Outputs: `coil_making_token.toml`, `ssw_scene.step`, `ssw_step_ledger.json`, and artifact metadata.
- Canonical state: fixed dimensions including the TV-to-TX spacing and MULL ferrite sheet thickness, shared ferrite position ratio, TX/RX coil parameters, RX explicit SSW-vs-normal/spiral mode, realized RX normal/spiral trace width, `tv`, derived `tx_region`, current-placement `tx_region_max`, TOML-sized `rx_region_max` non-model bounds/transparency resolved to the TV back face and bottom, SSW port-anchor world coordinates, RX normal/spiral back-side port placement, scene action tokens, generated part names, body bounds, and body roles in the ledger.
- Invariants: TX and RX modeled objects must exist once, all ranges in fixed mode have `min == max` and `count == 1`, dimensions are positive, TX is always an XY-plane SSW coil inside the derived `tx_region` with its port anchor on the lower `z_min` face, `rx_region_max` keeps its TOML Y/Z size envelope while its X max aligns to TV X max and its Z min aligns to TV Z min, RX uses a YZ-plane coil placed inside `rx_region_max`, RX may use coilmaker normal/spiral only when `is_ssw_enabled` is explicitly false, RX normal/spiral keeps quarter-turn settings in scene/action tokens with the realized port copper on the RX X-min back face and port pad size equal to realized trace width, MULL ferrite sheets have the same in-plane footprint as the current coil bounds, TX MULL ferrite placement uses `tx_region_max` as the outer boundary and RX MULL ferrite placement uses `rx_region_max` as the outer boundary, shared ratio `1.0` means coil-adjacent without overlap, TX/RX long dimensions follow the Y axis, `tx_region` is larger than the TX coil and its top equals `TV bottom - fixed_dimensions.tx_rx_min_distance_mm`, `tx_region_max` follows the current TX placement with 15 mm thickness, `rx_region_max` uses 5 mm thickness, token TOML is saved before STEP export, body names are unique, and CadQuery STEP export must produce a non-empty file.
- Fail-fast points: invalid TOML tables, missing parameter ranges, unfrozen fixed values, TX with SSW disabled, RX spiral quarter-turn values outside the coilmaker `0..7` and `0..3` ranges, ferrite ratio outside `0..1`, ferrite remaining interval smaller than sheet thickness, duplicate modeled object IDs, missing `tv` or `tx_region`, unsupported roles, invalid geometry dimensions, non-transformer-ready action tokens, unparseable token TOML, and failed STEP export.
- Collaborators: [coilmaker.py](coilmaker.py.md), [debug_view_0_3_0_ssw.py](../../../entry/debug_view_0_3_0_ssw.py.md).
- Tests: [test_ssw_step.py](../../../tests/test_ssw_step.py.md).
- Change hazards: keep RX explicit normal/spiral mode separate from fallback behavior; do not rotate TX into the TV plane, move the TX port anchor off the lower face, put TX MULL ferrite back on absolute `tx_region` bottom, move RX normal/spiral port copper back to the X-max/front face, make RX normal/spiral port edge length use the fixed pad cap instead of trace width, collapse `tx_region` into a coil-tight box, drop the sweep-maximum non-model boxes or MULL ferrite sheets from the action/export ledger, move RX out of the TV bottom region, or add fallback minimal two-port geometry.
- Related plan: [0.3.0 ssw fixed ocp viewer](../../../plans/0.3.0-ssw-fixed-ocp-viewer.md).
