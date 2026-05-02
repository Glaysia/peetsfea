---
title: Type2 Rect Void Boundary
created: 2026-05-03 @ 00:00
updated: 2026-05-03 @ 00:00
tags:
  - geometry
  - sdd
---

# Type2 Rect Void Boundary

이 문서는 reusable rectangular void single-coil core의 graph owner다.
현재 SDD reset에서는 RX/reusable core behavior만 active로 두고, TX shape-specific multilayer/bus contract는 future plan의 예외 링크로만 남긴다.

## Owned Surface
- Public facade and reusable coil contract: [tx_rect_void.py](../code/src/peetsfea/tx_rect_void.py.md)
- Runtime dataclasses, role profiles, and metadata shape: [tx_rect_void_types.py](../code/src/peetsfea/tx_rect_void_types.py.md)
- TOML parsing and sampled realization: [tx_rect_void_spec.py](../code/src/peetsfea/tx_rect_void_spec.py.md)
- Centerline planning: [tx_rect_void_centerline.py](../code/src/peetsfea/tx_rect_void_centerline.py.md)
- Pure geometry primitives: [tx_rect_void_geometry.py](../code/src/peetsfea/tx_rect_void_geometry.py.md)
- Export metadata surface: [tx_rect_void_export.py](../code/src/peetsfea/tx_rect_void_export.py.md)

## Direct Verification
- Reusable/RX core tests: [test_tx_rect_void.py](../code/tests/tx_rect_void/test_tx_rect_void.py.md)

## Exceptional Links
- Active type2 spec/parser ownership remains under [type2-spec-boundary](type2-spec-boundary.md).
- STEP/AEDT consumption of exported metadata remains under [type2-step-import-boundary](type2-step-import-boundary.md).
- TX outer companion role details remain plan-owned until promoted back into an active geometry contract.

## Invariants
- Invalid dimensions, unsupported turn counts, and geometry self-overlap fail immediately.
- `void_usage_ratio` is the canonical public void ownership input during the reset.
- Planned split notes may point at files that do not exist yet; their graph role is boundary design, not runtime evidence.
