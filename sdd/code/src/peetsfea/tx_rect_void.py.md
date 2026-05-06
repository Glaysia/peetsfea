---
title: tx_rect_void.py
created: 2026-04-17 @ 09:09
updated: 2026-05-06 @ 00:00
tags:
  - geometry
  - rx
---

# tx_rect_void.py

## Source
- Path: `src/peetsfea/tx_rect_void.py`
- Code note path: `sdd/code/src/peetsfea/tx_rect_void.py.md`
- Status: active
- Primary graph owner: [type2-rect-void-boundary](../../../architecture/type2-rect-void-boundary.md)

## 역할
- Historical module name aside, this note now documents the reusable rectangular void single-coil core for RX use.
- TX shape-specific multilayer/bus contracts are removed from SDD during the 0.2.24 reset.
- Re-exports the reusable central corridor helpers for callers that consume the public `peetsfea.tx_rect_void` facade.

## 입력 / 출력
- 입력: validated single-coil profile/spec
- 출력: deterministic PCB/copper geometry metadata for the reusable coil core, including local central void corridor Y bounds exposed from the export module

## Canonical state
- RX single-coil generation remains supported.
- Public type2 RX path uses centered `void_usage_ratio` and RX envelope usage ratios.

## Invariants / fail-fast
- Invalid dimensions, unsupported turn counts, and geometry self-overlap fail immediately.
- Do not restore TX multilayer or TX bus shape contracts here while the reset is active.
- Facade exports must preserve the export module's fail-fast corridor proof and must not introduce fallback geometry behavior.

## Graph links
- Primary owner: [type2-rect-void-boundary](../../../architecture/type2-rect-void-boundary.md)
- Direct child: [tx_rect_void_spec.py](tx_rect_void_spec.py.md)
- Direct child: [tx_rect_void_geometry.py](tx_rect_void_geometry.py.md)
- Export handoff: [tx_rect_void_export.py](tx_rect_void_export.py.md)
- Runtime consumer: [type2_step_export.py](type2_step_export.py.md)
