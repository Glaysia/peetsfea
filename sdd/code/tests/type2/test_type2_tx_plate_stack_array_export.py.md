---
title: test_type2_tx_plate_stack_array_export.py
created: 2026-04-20 @ 04:35
updated: 2026-04-20 @ 18:20
tags:
  - tests
  - step-export
  - tx
  - plate-stack
---

# test_type2_tx_plate_stack_array_export.py

## Source
- Path: `tests/type2/test_type2_tx_plate_stack_array_export.py`
- Code note path: `sdd/code/tests/type2/test_type2_tx_plate_stack_array_export.py.md`
- Status: planned
- Related plan: [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]]

## 역할
- TX plate-stack array STEP/ledger geometry contract를 검증한다.

## 입력 / 출력
- 입력: fixed and temporary type2 specs with `tx_coil_count = 1..4`
- 출력: pytest assertions for exact names, groups, branch placement, canonical coordinates, port metadata, and copper connectivity

## Canonical state
- `N=1` preserves old TX names.
- `N>1` uses branch-local non-copper names and one united `tx_plate_copper`.
- `g_copper_tx` contains exactly `tx_plate_copper`; `g_ferrite_tx` expands to all branch ferrite-family bodies.
- `tx_array_x_usage_ratio` reduces the full available branch-origin X span before copied-branch rotation.
- `b0` stays unrotated; `b1..` rotate with negative slope about their top far-side long edge so the free end tilts toward the RX bottom center.
- Rotated copied branches may extend outside `tx_region` in X but must stay inside `tx_region` in Z.
- Every copied branch hinge/top edge must remain aligned to `tx_region.max_z`.

## Invariants / fail-fast
- STEP labels must be unique and exact.
- Generic `SOLID*` drift is forbidden.
- TX array canonical bounds must touch `tx_region.max_z` and stay within owner Z bounds.
- Ratio-scaled unrotated branch origins must match `tx_array_x_usage_ratio`; final X bounds may grow after rotation.
- Adjacent-branch connector bridge solids must be fused into `tx_plate_copper`.
- Canonical coordinates must record rotation target, hinge edges, negative per-branch angles, and connector bridge
  provenance sufficient to audit branch-to-branch parallel connectivity.
- TX port metadata must match branch 0 terminal metadata, not the full array envelope.

## 직접 의존
- [[sdd/code/src/peetsfea/type2_plate_stack.py]]
- [[sdd/code/src/peetsfea/type2_tx_plate_stack_array.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]

## 관련 테스트
- This file is the direct export regression owner.

## 변경 시 주의점
- Do not relax existing RX plate-stack tests while adding TX array coverage.
- Keep body-name expectations synchronized with import tests.
