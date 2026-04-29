---
title: type2_rect_void_feasibility.py
created: 2026-04-29 @ 00:00
updated: 2026-04-29 @ 00:00
tags:
  - type2
  - constraints
  - geometry
---

# type2_rect_void_feasibility.py

## Source
- Path: `src/peetsfea/type2_rect_void_feasibility.py`
- Code note path: `sdd/code/src/peetsfea/type2_rect_void_feasibility.py.md`
- Status: active

## Responsibility
- Provide pure-Python rect/void feasibility math for sample-time constraints.
- Keep trace-width formulas shared with type2 sampling without importing STEP/CAD/AEDT modules.

## Inputs / outputs
- Inputs: concrete outer dimensions, turn count, void usage ratio, margin ratio, and metal fill factor.
- Outputs: minimum trace width in millimeters.

## Canonical state
- The minimum trace width calculation mirrors `tx_rect_void_spec.realize_tx_rect_void_spec()` for centered voids.
- The helper owns no persistent runtime state.

## Invariants / fail-fast
- Dimensions must be positive finite numbers.
- Ratios must be finite and inside their supported domains.
- Turn count must be positive.
- Void bounds must remain inside outer bounds with margin before trace width is calculated.

## Collaborators
- [type2_sampled_sampling.py](type2_sampled_sampling.py.md)
- [tx_rect_void_spec.py](tx_rect_void_spec.py.md)

## Related tests
- [test_sample_type2_entry.py](../../tests/type2/test_sample_type2_entry.py.md)

## Change hazards
- Formula changes must stay synchronized with `tx_rect_void_spec.realize_tx_rect_void_spec()`.
