---
title: test_tx_rect_void.py
created: 2026-04-18 @ 09:09
updated: 2026-05-06 @ 00:00
tags:
  - test
  - rx
---

# test_tx_rect_void.py

## Source
- Path: `tests/tx_rect_void/test_tx_rect_void.py`
- Code note path: `sdd/code/tests/tx_rect_void/test_tx_rect_void.py.md`
- Status: active
- Primary graph owner: [type2-rect-void-boundary](../../../architecture/type2-rect-void-boundary.md)

## 역할
- Reusable rectangular void single-coil core behavior를 검증한다.
- 0.2.24 SDD 기준 RX/reusable core only.

## Invariants / fail-fast
- `tx_coil.terminal_stub_length_mm` is treated as TOML-owned when present in the sampled range, and realization must use the selected value directly.
- Invalid geometry fails immediately.
- `tx_coil.terminal_stub_length_mm` resolve must be finite and > 0; non-positive values fail fast at realization.
- TX underlay/multilayer contracts are not covered by this note.
- Reusable copper primitive helpers must expose deterministic, finite central corridor Y bounds for TX inner-compatible rect-void geometry.
- The central corridor Y bounds must contain the realized central void Y bounds and exceed the realized void span for fixed-like 2-turn geometry where the copper-free central corridor is larger than the rectangular void; copper that starts at one void edge may keep that side coincident with the realized void.
- If the central corridor helper accepts primitive input, empty primitive input must fail fast instead of producing guessed bounds.

## Graph links
- Primary owner: [type2-rect-void-boundary](../../../architecture/type2-rect-void-boundary.md)
- Direct verification: [tx_rect_void.py](../../src/peetsfea/tx_rect_void.py.md)
- Direct verification: [tx_rect_void_geometry.py](../../src/peetsfea/tx_rect_void_geometry.py.md)
