---
title: type2_single_coil_underlay.py
created: 2026-04-20 @ 00:00
updated: 2026-04-28 @ 00:00
tags:
  - rx
  - non-model
---

# type2_single_coil_underlay.py

## Source
- Path: `src/peetsfea/type2_single_coil_underlay.py`
- Code note path: `sdd/code/src/peetsfea/type2_single_coil_underlay.py.md`
- Status: active

## 역할
- RX single-coil backing/context geometry helper다.
- TX underlay shape contract is removed from SDD for the 0.2.24 reset.

## Canonical state
- RX backing/context behavior remains documented only where RX owns it.

## Invariants / fail-fast
- Invalid RX placement or dimensions fail immediately.
- Do not restore TX underlay shape rules here during the reset.
