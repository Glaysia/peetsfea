---
title: type2_tx_plate_stack_array.py
created: 2026-04-20 @ 04:35
updated: 2026-04-20 @ 15:05
tags:
  - step-export
  - tx
  - plate-stack
  - array
---

# type2_tx_plate_stack_array.py

## Source
- Path: `src/peetsfea/type2_tx_plate_stack_array.py`
- Code note path: `sdd/code/src/peetsfea/type2_tx_plate_stack_array.py.md`
- Status: planned
- Related plan: [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]]

## 역할
- TX plate-stack branch placement, branch-local final body names, and parallel sheet connector geometry helpers를 담당한다.
- oversized `type2_plate_stack.py`가 branch array arithmetic을 직접 더 떠안지 않도록 분리된 helper boundary다.

## 입력 / 출력
- 입력: TX/RX owner bounds, realized TX count, active Y/Z windows, plate-stack thickness values, branch source body specs
- 출력: branch placement descriptors, branch-local final names, per-adjacent-branch sheet connector faces, array-level canonical coordinates and metadata fragments

## Canonical state
- `tx_coil_count = 1`은 existing single-branch exact-name compatibility mode다.
- `tx_coil_count > 1`은 `tx_region.min_x` 기준 `+X` branch placement를 사용한다.
- `tx_array_x_usage_ratio` scales the full available branch-origin X span; `1.0` reproduces the previous full-span placement and requested sweeps use `0.1..0.6`.
- Branch `b0` stays in the unrotated compatibility orientation.
- Branches `b1..b{N-1}` rotate with negative slope about their top far-side long edge so the free end tilts toward the `rx_region_max` bottom-face center.
- Every branch active Z window is top-aligned to `tx_region.max_z` before rotation; rotated copied branches must keep bounding Z inside `tx_region`.
- X placement may overflow `tx_region` after copied-branch rotation; Z placement may not.
- Canonical coordinates record copied-branch hinge edges, negative rotation angles, rotation target,
  and every adjacent-branch connector sheet's four world vertices by exact sheet name.
- branch-local final names use `tx_b{i}_...` naming, including `tx_b{i}_plate_copper`.
- TX branches are electrically parallel-connected by `N-1` input connector sheets and `N-1` output connector sheets built from transformed adjacent branch terminal edges.
- Connector sheets remain sheet faces with zero solids; they are not extruded, thickened, boxed, or united into `tx_plate_copper`.
- Connector sheet vertices are emitted into ledger metadata so AEDT import can reconstruct those sheet conductors without
  relying on STEP free-surface shell import behavior.
- `g_copper_tx.member_body_names` follows `expected_exported_body_names` order exactly: branch copper bodies first,
  then connector sheets interleaved by adjacent segment (`input_s0`, `output_s0`, `input_s1`, `output_s1`, ...).

## Invariants / fail-fast
- `1 <= tx_coil_count <= 4`
- `0 < tx_array_x_usage_ratio <= 1`
- unrotated branch origins must keep each branch total thickness inside `tx_region`.
- copied-branch rotation target must be physically meaningful: RX bottom center must be above the TX top hinge plane and at larger X than the branch hinge X.
- rotated copied branches must not exceed `tx_region` Z bounds.
- branch-local final body names must be unique and <= AEDT name length constraints already enforced by export helpers.
- input and output connector sheets must not collapse into the same conductor path before branch coils connect them through branch geometry.
- connector sheet labels must resolve to exactly one face and zero solids in export tests.
- each connector sheet name in `expected_exported_body_names` must have exactly four canonical vertices recorded under
  `canonical_coordinates.connector_sheet_vertices_xyz_by_name`.
- helper must not create additional modeled ledger entries or additional TX ports.

## 직접 의존
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_plate_stack.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/type2_plate_stack.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_type2_tx_plate_stack_array_export.py]]

## 변경 시 주의점
- helper는 geometry owner가 아니라 TX array arithmetic/label owner다. RX plate-stack geometry must remain shared baseline behavior.
- parallel sheet connector behavior must stay single-port compatible with setup-ready EM path.
- Do not route `tx_single_coil` through this module.
