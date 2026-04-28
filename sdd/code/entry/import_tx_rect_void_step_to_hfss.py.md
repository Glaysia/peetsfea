---
title: import_tx_rect_void_step_to_hfss.py
created: 2026-04-17 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - entry
  - legacy
  - import
---

# import_tx_rect_void_step_to_hfss.py

## Source
- Path: `entry/import_tx_rect_void_step_to_hfss.py`
- Code note path: `sdd/code/entry/import_tx_rect_void_step_to_hfss.py.md`
- Status: legacy / opt-in

## 역할
- Historical rect/void coil import smoke entrypoint다.
- Active type2 RxOnly import/setup path is `entry/import_type2_step.py` and setup-ready build flow.

## Invariants / fail-fast
- Import failures raise immediately.
- Do not use this note to define active transmitter geometry or ports.

## Related
- [[sdd/code/tests/backend_em/test_tx_rect_void_step_import_smoke.py]]
