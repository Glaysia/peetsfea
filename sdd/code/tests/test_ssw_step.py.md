---
title: test_ssw_step.py
created: 2026-06-07
updated: 2026-06-14
tags:
  - sdd
  - code
  - test
---

# test_ssw_step.py

- Path: `tests/test_ssw_step.py`
- Responsibility: verify the 0.3.0 fixed SSW TOML parser and CadQuery STEP artifact contract.
- Inputs: temporary fixed TOML files and monkeypatched CadQuery export behavior.
- Outputs: pytest assertions for parsed TX/TX-under/RX parameters, parsed SSW constraints, failed non-coprime turn/twist constraints, failed RX SSW single-turn constraints, TX/RX MULL ferrite enable flags, split TX/RX MULL ferrite settings, derived `tx_region` spacing, TX max-region bounds, TOML-sized `rx_region_max` bounds with TV back-face X alignment and TV-bottom Z alignment, RX placement inside `rx_region_max`, TX/RX port-anchor placement, RX normal/spiral back-side port placement for explicit RX spiral mode, AEDT semantic edge endpoint ledger generation, short identity metadata, MULL ferrite sheet placement/suppression, RX explicit normal/spiral export, non-model transparency, parseable token TOML, generated ledger names, and fail-fast export handling.
- Canonical state: the expected shared fixed dimensions plus TX/TX-under/RX modeled object roles, SSW fields, under-coil enable fields, TX/RX MULL ferrite enable fields, constraint rules, and RX explicit normal/spiral fields.
- Invariants: fixed ranges are frozen, TX/TX-under/RX fields are complete, MULL ferrite enable flags are frozen 0/1 integer flags, default fixed TOML generates TX MULL ferrite and suppresses RX MULL ferrite, swapped flags generate only RX MULL ferrite, SSW constraints reject non-coprime enabled turn/twist values and RX SSW `turn_n_int <= 1` when enabled, generated body names include TX/RX coils and only currently enabled optional bodies, `tv`, `tx_region`, `tx_region_max`, and `rx_region_max` are the active non-model bodies, `tx_region_max` follows current TX placement with 55 mm thickness, `rx_region_max` keeps its TOML Y/Z size envelope, uses 5 mm X thickness, aligns X max to TV X max, and aligns Z min to TV Z min, TX main remains on the XY plane inside a larger `tx_region` with its port anchor on the lower Z face, TX MULL ferrite uses `tx_mull_position_ratio` on the TX Z interval, RX explicit normal/spiral emits normal copper/action tokens and preserves quarter-turn settings including the valid `0,0` selection, AEDT port ledger references existing copper bodies and semantic edge endpoints instead of appending sheet bodies, identity metadata uses `0_3_0_p*` without entering body names, TX main and RX keep their long dimension on Y, token TOML contains all non-model boxes plus present TX/RX namespaced action tokens, present MULL ferrite sheet tokens, and scene placement/export actions, and failed STEP export raises after token TOML has already been written.
- Fail-fast points: missing fields, unfrozen ranges, malformed or failed constraints, duplicate names, and failed export.
- Collaborators: [ssw_step.py](../src/peetsfea/ssw_step.py.md).
- Related plan: [0.3.0 ssw fixed ocp viewer](../../plans/0.3.0-ssw-fixed-ocp-viewer.md).
- Identity plan: [0.3.0 ssw aedt design space identity](../../plans/0.3.0-ssw-aedt-design-space-identity.md).
