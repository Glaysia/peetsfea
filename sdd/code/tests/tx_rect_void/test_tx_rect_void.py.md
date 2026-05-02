---
title: test_tx_rect_void.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - test
  - rx
---

# test_tx_rect_void.py

## Source
- Path: `tests/tx_rect_void/test_tx_rect_void.py`
- Code note path: `sdd/code/tests/tx_rect_void/test_tx_rect_void.py.md`
- Status: active

## 역할
- Reusable rectangular void single-coil core behavior를 검증한다.
- 0.2.24 SDD 기준 RX/reusable core only.

## Invariants / fail-fast
- `tx_coil.terminal_stub_length_mm` is treated as TOML-owned when present in the sampled range, and realization must use the selected value directly.
- Invalid geometry fails immediately.
- `tx_coil.terminal_stub_length_mm` resolve must be finite and > 0; non-positive values fail fast at realization.
- TX underlay/multilayer contracts are not covered by this note.

## Collaborators
- [tx_rect_void.py](../../src/peetsfea/tx_rect_void.py.md)
