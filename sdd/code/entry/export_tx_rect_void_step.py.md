---
title: export_tx_rect_void_step.py
created: 2026-04-17 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - entry
  - legacy
  - step-export
---

# export_tx_rect_void_step.py

## Source
- Path: `entry/export_tx_rect_void_step.py`
- Code note path: `sdd/code/entry/export_tx_rect_void_step.py.md`
- Status: legacy / opt-in

## 역할
- Historical rect/void coil STEP smoke entrypoint다.
- Active type2 RxOnly flow must not depend on this entrypoint.

## Invariants / fail-fast
- CLI failures raise immediately.
- Do not use this note to define active transmitter geometry.

## Related
- [[sdd/plans/0.2.24-type2-rxonly-tx-removal]]
- [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py]]
