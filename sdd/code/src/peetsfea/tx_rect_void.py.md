---
title: tx_rect_void.py
created: 2026-04-17 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - geometry
  - rx
---

# tx_rect_void.py

## Source
- Path: `src/peetsfea/tx_rect_void.py`
- Code note path: `sdd/code/src/peetsfea/tx_rect_void.py.md`
- Status: active

## 역할
- Historical module name aside, this note now documents the reusable rectangular void single-coil core for RX use.
- TX shape-specific multilayer/bus contracts are removed from SDD during the 0.2.24 reset.

## 입력 / 출력
- 입력: validated single-coil profile/spec
- 출력: deterministic PCB/copper geometry metadata for the reusable coil core

## Canonical state
- RX single-coil generation remains supported.
- Public type2 RX path uses centered `void_usage_ratio` and RX envelope usage ratios.

## Invariants / fail-fast
- Invalid dimensions, unsupported turn counts, and geometry self-overlap fail immediately.
- Do not restore TX multilayer or TX bus shape contracts here while the reset is active.

## Collaborators
- [tx_rect_void_spec.py](tx_rect_void_spec.py.md)
- [tx_rect_void_geometry.py](tx_rect_void_geometry.py.md)
- [type2_step_export.py](type2_step_export.py.md)
