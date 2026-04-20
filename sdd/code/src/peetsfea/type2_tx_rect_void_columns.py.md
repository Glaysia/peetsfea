---
title: type2_tx_rect_void_columns.py
created: 2026-04-20 @ 23:55
updated: 2026-04-20 @ 23:55
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

## Single responsibility
- Build axis-aligned geometry-only `tx_rect_void_columns` tile bodies (PCB and copper per layer) from resolved stack-space members before export applies stack-space tilt transforms.

## Inputs / outputs
- Inputs: `ModeledTxRectVoidColumnsSpec`, resolved `tx_region_actual_stack_space` `NonModelBoxSpec` members, seed.
- Outputs: deterministic per-tile `bd.Shape` tuples and flattened deterministic expected body-name order.

## Canonical state
- Uses `tx_region_actual_stack_space` concrete members as canonical per-tile owners.
- Uses the full stack-space footprint as the rect/void coil outer envelope; there are no TX columns outer usage-ratio owners.
- Reuses one resolved X-column turn-count owner per realized X index across all Y tiles for that X.
- Produces exactly one PCB and one copper body per layer for each realized X/Y tile.
- Uses the TX columns `layer_gap_mm` only for geometry-only layer placement. The reusable rect/void core is called in single-layer mode with a core-compatible gap when needed, so the core's multilayer connection constraint does not define TX columns spacing.

## Invariants / fail-fast
- Stack-space tile IDs must follow concrete `tx_region_actual_stack_space_x{X}_y{Y}` contract (or root singleton).
- Realized X indices must be contiguous zero-based and in `[0, 2]`; realized layer count must be in `[1, 3]`.
- The resolved full layer stack height, including TX columns `layer_gap_mm`, must fit inside the owning stack-space height.
- Body names are deterministic, globally unique, and length-capped for AEDT-friendly import.
- No ferrite/underlay/stack/bus/port-sheet bodies are generated in this module.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]

## Related tests
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## Change hazards
- Any change to naming prefixes/order must stay synchronized with export-side modeled expected-body validation and metadata consumers.
- Placement offsets are anchored to stack-space owner bounds; drift can violate tilted-owner containment checks in export.
