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
- Outputs: pytest assertions for parsed TX/RX parameters, derived `tx_region` spacing, RX-in-TV placement, non-model transparency, parseable token TOML, generated ledger names, and fail-fast export handling.
- Canonical state: the expected shared fixed dimensions plus TX/RX modeled object roles and eight fixed SSW fields per side.
- Invariants: fixed ranges are frozen, TX/RX fields are complete, generated body names include both coil roles, `tv` and `tx_region` are the active non-model bodies, TX remains on the XY plane inside a larger `tx_region`, RX remains on the YZ plane inside the TV with FR4 bottom alignment, both coils keep their long dimension on Y, token TOML contains TX/RX namespaced action tokens and scene placement/export actions, and failed STEP export raises after token TOML has already been written.
- Fail-fast points: missing fields, unfrozen ranges, duplicate names, and failed export.
- Collaborators: [ssw_step.py](../src/peetsfea/ssw_step.py.md).
- Related plan: [0.3.0 ssw fixed ocp viewer](../../plans/0.3.0-ssw-fixed-ocp-viewer.md).
