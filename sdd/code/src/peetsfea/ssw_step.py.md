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
- Responsibility: parse the 0.3.0 fixed SSW TOML surface, place coilmaker TX/RX SSW assemblies in the TV scene, and generate CadQuery STEP geometry, action-token TOML, and a JSON ledger.
- Inputs: `examples/0.3.0_fixed.toml`, output directory, seed.
- Outputs: `coil_making_token.toml`, `ssw_scene.step`, `ssw_step_ledger.json`, and artifact metadata.
- Canonical state: fixed dimensions including the TV-to-TX spacing, TX/RX coil parameters, `tv` and derived `tx_region` non-model bounds/transparency, scene action tokens, generated part names, body bounds, and body roles in the ledger.
- Invariants: TX and RX modeled objects must exist once, all ranges in fixed mode have `min == max` and `count == 1`, dimensions are positive, RX is a YZ-plane SSW coil inside the TV with FR4 aligned to the TV bottom and copper overhang limited to copper thickness, TX is an XY-plane SSW coil inside the derived `tx_region`, TX/RX long dimensions follow the Y axis, `tx_region` is larger than the TX coil and its top equals `TV bottom - fixed_dimensions.tx_rx_min_distance_mm`, token TOML is saved before STEP export, body names are unique, and CadQuery STEP export must produce a non-empty file.
- Fail-fast points: invalid TOML tables, missing parameter ranges, unfrozen fixed values, duplicate modeled object IDs, missing `tv` or `tx_region`, unsupported roles, invalid geometry dimensions, non-transformer-ready action tokens, unparseable token TOML, and failed STEP export.
- Collaborators: [coilmaker.py](coilmaker.py.md), [debug_view_0_3_0_ssw.py](../../../entry/debug_view_0_3_0_ssw.py.md).
- Tests: [test_ssw_step.py](../../../tests/test_ssw_step.py.md).
- Change hazards: keep SSW-specific fields separate from deprecated normal-coil and serial-coil fields; do not rotate TX into the TV plane, collapse `tx_region` into a coil-tight box, move RX out of the TV bottom region, or add fallback minimal two-port geometry.
- Related plan: [0.3.0 ssw fixed ocp viewer](../../../plans/0.3.0-ssw-fixed-ocp-viewer.md).
