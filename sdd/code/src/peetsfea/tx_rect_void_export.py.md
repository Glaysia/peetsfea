---
title: tx_rect_void_export.py
created: 2026-04-18 @ 09:09
updated: 2026-05-06 @ 00:00
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
- TX underlay and TX multilayer shape contracts remain outside this reusable core note, but reusable copper primitive data may be used by Type2 TX inner passive geometry to derive copper-free central corridor bounds.

## Inputs / outputs
- Input: validated `RealizedSingleCoilRectVoid` plus a single-coil profile for labels and terminal stub semantics.
- Output: deterministic box/STEP metadata and local central corridor Y bounds for the realized centered void X strip.

## Canonical state
- RX core export metadata remains deterministic.
- Port sheets are runtime metadata, not STEP bodies.
- Copper primitive polygons remain the source of truth for positive-area overlap checks when downstream Type2 helpers need to find copper-free gaps around the centered void.
- `central_corridor_y_bounds()` accepts caller-supplied copper primitives for testable fail-fast validation and returns the proven local `RectBounds` over the selected void X strip.
- `local_central_void_corridor_y_bounds()` derives the corridor from layer-0 copper primitives built from the canonical centerline path and returns only the proven local `(min_y, max_y)` interval.

## Invariants / fail-fast
- Invalid RX core geometry fails immediately.
- Central corridor derivation must fail rather than guessing if copper primitive polygons cannot prove a positive copper-free interval around the realized void strip.
- Central corridor derivation clips copper primitive polygons to the selected void X strip and uses the nearest strict above/below blockers from that clipped area.
- Central corridor derivation fails if the realized void strip has non-positive bounds, the void intersects copper, no above/below blocker overlaps the selected X strip, the derived corridor has non-positive Y extent, or the final corridor rectangle overlaps copper with positive area.

## Collaborators / tests
- Direct tests: `tests/tx_rect_void/test_tx_rect_void.py`
- Verification commands: `../.venv/bin/pytest ../tests/tx_rect_void/test_tx_rect_void.py -q` from `run/`; `.venv/bin/pyright src/peetsfea/tx_rect_void_export.py src/peetsfea/tx_rect_void.py` from repo root.

## Change hazards
- Do not replace the copper primitive path with derived spacing or centerline-only guesses.
- Keep the helper local-coordinate only; world placement belongs to downstream modeled-object exporters.

## Graph links
- Primary owner: [type2-rect-void-boundary](../../../architecture/type2-rect-void-boundary.md)
- Parent facade: [tx_rect_void.py](tx_rect_void.py.md)
- Direct geometry collaborator: [tx_rect_void_geometry.py](tx_rect_void_geometry.py.md)
- Direct centerline collaborator: [tx_rect_void_centerline.py](tx_rect_void_centerline.py.md)
