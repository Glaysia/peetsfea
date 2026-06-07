---
title: test_ssw_step.py
created: 2026-06-07
updated: 2026-06-07
tags:
  - sdd
  - code
  - test
---

# test_ssw_step.py

- Path: `tests/test_ssw_step.py`
- Responsibility: verify the 0.3.0 fixed SSW TOML parser and CadQuery STEP artifact contract.
- Inputs: temporary fixed TOML files and monkeypatched CadQuery export behavior.
- Outputs: pytest assertions for parsed TX/RX parameters, derived `tx_region` spacing, TX max-region bounds, TV-derived `rx_region_max` bounds, RX maximum-X placement inside `rx_region_max`, TX/RX port-anchor placement, RX explicit normal/spiral export, non-model transparency, parseable token TOML, generated ledger names, and fail-fast export handling.
- Canonical state: the expected shared fixed dimensions plus TX/RX modeled object roles, SSW fields, and RX explicit normal/spiral fields.
- Invariants: fixed ranges are frozen, TX/RX fields are complete, generated body names include both coil roles, `tv`, `tx_region`, `tx_region_max`, and `rx_region_max` are the active non-model bodies, `tx_region_max` follows current TX placement with 15 mm thickness, `rx_region_max` is derived from TV bounds and uses 5 mm X thickness, TX remains on the XY plane inside a larger `tx_region` with its port anchor on the lower Z face, RX defaults to normal/spiral when `is_ssw_enabled` is false, RX explicit normal/spiral emits normal copper/action tokens and preserves quarter-turn settings including the valid `0,0` selection, RX is placed at the maximum-X side of `rx_region_max`, both coils keep their long dimension on Y, token TOML contains all non-model boxes plus TX/RX namespaced action tokens and scene placement/export actions, and failed STEP export raises after token TOML has already been written.
- Fail-fast points: missing fields, unfrozen ranges, duplicate names, and failed export.
- Collaborators: [ssw_step.py](../src/peetsfea/ssw_step.py.md).
- Related plan: [0.3.0 ssw fixed ocp viewer](../../plans/0.3.0-ssw-fixed-ocp-viewer.md).
