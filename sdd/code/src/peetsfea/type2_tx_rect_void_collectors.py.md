---
title: type2_tx_rect_void_collectors.py
created: 2026-04-21 @ 23:55
updated: 2026-04-22 @ 02:10
tags:
  - type2
  - tx
  - rect-void
  - collectors
---

# type2_tx_rect_void_collectors.py

## Source
- Path: `src/peetsfea/type2_tx_rect_void_collectors.py`
- Code note path: `sdd/code/src/peetsfea/type2_tx_rect_void_collectors.py.md`
- Status: implemented
- Primary plan: [[sdd/plans/0.2.22-type2-tx-rect-void-columns-geometry]]

## Single responsibility
- Build underside collector geometry for `tx_rect_void_columns` after tile tilt and vertical terminal-stub generation, producing a two-tab future port handoff for realized `connection_mode = 0` parallel and `connection_mode = 1` series.

## Inputs / outputs
- Inputs: `TxRectVoidCollectorTileInput` records with `x_index`, `y_index`, per-tile copper shapes, start/end terminal stub solids, start/end pickup rectangle vertices, and shared copper thickness.
- Outputs: deterministic collector source solids, one fused copper handoff body, grouped source labels, two external terminal-tab face vertex sets, and mode-specific audit data.

## Canonical state
- The module owns the collector source geometry only; it does not alter TOML/spec schema or export dispatch.
- Start collectors occupy the upper underside collector layer; end collectors occupy the lower layer with fixed 0.5 mm clearance.
- Same-polarity collectors are broad pours, not thin line routes. Start pours use a low-X bus plus branch-local pour patches to start pickups; end pours use a high-X bus plus branch-local pour patches to end pickups.
- Series collectors use deterministic boustrophedon order and local broad straps from each tile end pickup to the next tile start pickup.
- Pours must not become full-array overlapping planes for both polarities; the overlap audit remains a hard contract.
- The export-ready fused body is always labeled `tx_rect_void_columns_copper`.
- The external port handoff exposes exactly two tab face vertex sets, one for start and one for end.

## Invariants / fail-fast
- `connection_mode` must be 0 or 1.
- Empty tile input is rejected immediately.
- Every realized tile must expose one start pickup and one end pickup, and the pickup rectangles must be 4-vertex shapes with positive span.
- Collector source labels are deterministic and unique before fusion. Pour labels replace the previous row-rail/spine/feed label family.
- The fused TX copper handoff must be exactly one solid.
- Start and end collector source solids must not have positive-volume intersection.
- Aggregate start/end collector feed length must balance within numeric tolerance, and per-branch spread is bounded by the internal branch-spread limit after tilt.
- Series collector links must not create positive-volume shortcuts between non-neighbor links or between the two external tabs.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_export.py]]
- [[sdd/code/src/peetsfea/type2_tx_rect_void_columns.py]]
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## Related tests
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## Change hazards
- Do not add public TOML fields for collector sizing in this phase; constants are internal to the geometry handoff.
- Do not emit a reconstructed HFSS port sheet or source assignment from this module.
- Do not route hybrid series-parallel collectors through this module.
- Do not reintroduce same-polarity thin trace routing as the primary current path; same-polarity connection must be pour-first.
- Keep the collector union fail-fast behavior; disconnected solids are a hard error.
