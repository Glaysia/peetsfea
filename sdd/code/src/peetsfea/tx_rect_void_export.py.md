---
title: tx_rect_void_export.py
created: 2026-04-18 @ 09:09
updated: 2026-05-03 @ 00:00
tags:
  - rx
  - export
---

# tx_rect_void_export.py

## Source
- Path: `src/peetsfea/tx_rect_void_export.py`
- Code note path: `sdd/code/src/peetsfea/tx_rect_void_export.py.md`
- Status: active
- Primary graph owner: [type2-rect-void-boundary](../../../architecture/type2-rect-void-boundary.md)

## 역할
- Historical module name aside, this note documents reusable/RX single-coil export metadata.
- TX underlay, TX port-sheet, and TX multilayer shape contracts are removed from SDD for the reset.

## Canonical state
- RX core export metadata remains deterministic.
- Port sheets are runtime metadata, not STEP bodies.

## Invariants / fail-fast
- Invalid RX core geometry fails immediately.

## Graph links
- Primary owner: [type2-rect-void-boundary](../../../architecture/type2-rect-void-boundary.md)
- Parent facade: [tx_rect_void.py](tx_rect_void.py.md)
- Direct geometry collaborator: [tx_rect_void_geometry.py](tx_rect_void_geometry.py.md)
- Direct centerline collaborator: [tx_rect_void_centerline.py](tx_rect_void_centerline.py.md)
