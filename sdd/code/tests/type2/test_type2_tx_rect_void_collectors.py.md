---
title: test_type2_tx_rect_void_collectors.py
created: 2026-04-21 @ 20:35
updated: 2026-04-21 @ 20:35
tags:
  - tests
  - type2
  - tx
  - collectors
---

# test_type2_tx_rect_void_collectors.py

## Source
- Path: `tests/type2/test_type2_tx_rect_void_collectors.py`
- Code note path: `sdd/code/tests/type2/test_type2_tx_rect_void_collectors.py.md`
- Status: active
- Primary plan: [[sdd/plans/0.2.22-type2-tx-rect-void-columns-geometry]]

## Single responsibility
- Hold the focused collector-module regression surface for `tx_rect_void_columns` parallel underside collector pour routing.

## Inputs / outputs
- Inputs: synthetic build123d copper/stub boxes and the collector module API.
- Outputs: pour bus/patch label determinism, fused-copper, branch-balance, overlap, and future tab-face contract assertions.

## Canonical state
- Synthetic helper boxes stay small, axis-aligned, and deterministic so collector pour assertions stay focused.
- Active coverage verifies `1x1`, `3x3`, and series-mode rejection for `connection_mode = 1`.

## Invariants / fail-fast
- Do not turn this file into a broad STEP export regression.
- Keep the collector surface isolated from existing `tests/type2/test_generate_type2_step.py` coverage.
- The collector module should continue to fail fast on unsupported setup-ready routing paths rather than degrade into a fallback.

## Collaborators
- [[sdd/code/src/peetsfea/type2_tx_rect_void_collectors.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]

## Related tests
- [[sdd/code/tests/type2/test_generate_type2_step.py]]
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]

## Change hazards
- Do not merge the scaffold into the broad export test file; keep the collector contract in its own focused surface.
