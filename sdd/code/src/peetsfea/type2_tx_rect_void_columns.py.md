---
title: type2_tx_rect_void_columns.py
created: 2026-04-20 @ 23:55
updated: 2026-04-22 @ 01:10
tags:
  - type2
  - tx
  - rect-void
  - geometry
---

# type2_tx_rect_void_columns.py

## Source
- Path: `src/peetsfea/type2_tx_rect_void_columns.py`
- Code note path: `sdd/code/src/peetsfea/type2_tx_rect_void_columns.py.md`
- Status: active
- Primary plan: [[sdd/plans/0.2.22-type2-tx-rect-void-columns-geometry]]
- Performance plan: [[sdd/plans/0.2.23-rect-void-fast-face-export]]

## Single responsibility
- Build axis-aligned geometry-only `tx_rect_void_columns` tile coil bodies and terminal-anchor metadata from resolved stack-space members, resolving mode-aware per-tile turn counts from `connection_mode`, `equivalent_turn_count`, turn weights, and center-weighted contracts before export applies stack-space tilt transforms and appends the tile-level terminal stubs.

## Inputs / outputs
- Inputs: `ModeledTxRectVoidColumnsSpec`, resolved `tx_region_actual_stack_space` `NonModelBoxSpec` members, explicit `rx_center_xyz`, seed.
- Outputs: deterministic per-tile `bd.Shape` tuples, mode-aware per-tile resolved turn counts, `connection_mode`, exactly two deterministic tile-level terminal body names (`_stub_s`, `_stub_e`) per tile, per-layer terminal-anchor BoxSpec groups for start/end, and flattened deterministic expected body-name order.

## Canonical state
- Uses `tx_region_actual_stack_space` concrete members as canonical per-tile owners.
- Uses the full stack-space footprint as the rect/void coil outer envelope; there are no TX columns outer usage-ratio owners.
- Uses a single shared tx_columns owner plus deterministic per-tile resolved turn allocation from `resolve_tx_turns` with the mode-aware `equivalent_turn_count` interpretation.
- Turn allocation uses normalized TX-plane 2D distance to the RX center projection from `rx_center_xyz`; equal-distance tiles must resolve to equal turn counts.
- Uses a TX columns internal `SingleCoilProfile` sized for the mode-specific cap: parallel branches are constrained to `1..10`, while series total physical turns are constrained to `<= 31`.
- `connection_mode = 0` interprets `equivalent_turn_count` through the parallel harmonic branch formula `1 / sum(1 / n_i)`; `connection_mode = 1` interprets it as the full series-chain physical turn-sum target.
- Uses the public `equivalent_turn_count` owner directly in both modes; legacy public `series_total_turn_count` and `parallel_total_turn_count` are not read.
- Resolves `layer_count` and `layer_gap_mm` as a deterministic feasible pair constrained by the concrete stack-space height.
- Fast export scales/translates the local segment-face footprint and terminal-stub BoxSpec anchors first, then creates one base-layer copper/PCB solid pair directly (without `build_tx_rect_void_step_scene`) and replicates it by Z-shift for multilayer tiles.
- Produces exactly one PCB and one copper coil body per realized X/Y layer, then one tile-level start terminal body and one tile-level end terminal body per realized X/Y tile (total `layer_count * 2 + 2`).
- Uses the TX columns `layer_gap_mm` only for geometry-only layer placement. The reusable rect/void core is called in single-layer mode with a core-compatible gap when needed, so the core's multilayer connection constraint does not define TX columns spacing.
- Uses `terminal_stub_length_mm` as the requested floorward stub length. Multilayer start/end terminal anchors are grouped by terminal so export can create one parallel collector plus floorward stub body per terminal.
- Exposes per-tile resolved turn counts and resolved `connection_mode` in `TxRectVoidColumnsBuildResult` metadata for downstream modeled export.

## Canonical naming
- PCB names follow `txrvc_x{X}_y{Y}_pcb_l{L}`.
- Copper names follow `txrvc_x{X}_y{Y}_cu_l{L}`.
- Terminal body names follow `txrvc_x{X}_y{Y}_stub_{s|e}` when within 32-char AEDT limit; otherwise deterministic hash-based truncation preserves uniqueness.

## Invariants / fail-fast
- Stack-space tile IDs must follow concrete `tx_region_actual_stack_space_x{X}_y{Y}` contract (or root singleton).
- Realized X indices must be contiguous zero-based and in `[0, 2]`; resolved layer count must be in `[1, 4]`.
- Resolved per-tile turns are bounded by the tx_rect_void_columns profile cap. Series may not exceed 31 total physical turns; parallel may not exceed 10 turns on any branch and must report the harmonic equivalent semantics.
- The resolved full layer stack height, including TX columns `layer_gap_mm`, must fit inside the owning stack-space height.
- Body names are deterministic, globally unique, and length-capped for AEDT-friendly import.
- No ferrite/underlay/stack/bus/port-sheet bodies are generated in this module; start/end terminal bodies are copper-only geometry and do not introduce cross-tile connection semantics.
- Fast geometry path does not pre-build any build123d scene for bounds/anchors; bounds/anchors come from scaled/translated `BoxSpec` state, and base solids come from 2D segment-face union extrusion + cut/fuse.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]

## Related tests
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## Change hazards
- Any change to naming prefixes/order must stay synchronized with export-side modeled expected-body validation and metadata consumers.
- Placement offsets are anchored to stack-space owner bounds; drift can violate tilted-owner containment checks in export.
