---
title: type2_step_spec.py
created: 2026-04-17 @ 09:09
updated: 2026-04-20 @ 21:35
tags:
  - step-export
  - spec
---

# type2_step_spec.py

## Source
- Path: `src/peetsfea/type2_step_spec.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_spec.py.md`
- Status: active
- Related feature plans: [[sdd/plans/0.2.22-type2-rx-plate-stack-striped-copper]], [[sdd/plans/0.2.22-type2-tx-rx-shared-plate-stack-import-only]], [[sdd/plans/0.2.22-type2-remove-plate-stack-shoe-contract]], [[sdd/plans/0.2.22-type2-plate-stack-equivalent-3-slab]], [[sdd/plans/0.2.22-type2-plate-stack-z-usage-ratio]], [[sdd/plans/0.2.22-type2-plate-stack-y-usage-ratio]], [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]]

## 역할
- type2 TOML object registry를 typed non-model / modeled spec으로 정규화한다.
- active modeled role set에 `tx_plate_stack`와 `rx_plate_stack`를 포함한 role-aware parser contract를 소유한다.

## 입력 / 출력
- 입력: type2 TOML path
- 출력: parsed type2 step spec, parsed modeled/non-model objects, parsed `outputs`

## Canonical state
- active plate roles는 `tx_plate_stack`와 `rx_plate_stack`다.
- active type2 schema id는 `peetsfea.type2.step.v4`다.
- TX plate object/owner/plane은 `tx_plate_stack` / `tx_region` / `YZ`다.
- RX plate object/owner/plane은 `rx_plate_stack` / `rx_region_max` / `YZ`다.
- TX plate role public fields are `pcb_total_thickness_mm`, `copper_thickness_mm`, `turn_count`, `metal_fill_factor`, `z_usage_ratio`, `y_usage_ratio`, `tx_coil_count`, `tx_array_x_usage_ratio`.
- RX plate role public fields remain `pcb_total_thickness_mm`, `copper_thickness_mm`, `turn_count`, `metal_fill_factor`, `z_usage_ratio`, `y_usage_ratio`.
- single-coil public outer envelope fields are `outer_x_usage_ratio` and `outer_y_usage_ratio`, not mm fields.
- single-coil `void_*` public fields are removed; the reusable core keeps centered `0.3 x 0.3` void geometry as an internal fixed contract.
- `render_tx_rect_void_toml()` is a compatibility bridge into the reusable core and must omit removed core `void_*` range tables; the core owns the fixed centered void ratios.
- `tx_coil_count` is TX-only and means total parallel-connected TX plate-stack branches including the original.
- `tx_array_x_usage_ratio` is TX-only and scales the full available TX array branch-origin X span, where `1.0` preserves full-span placement.
- plate `turn_count`는 wall-side copper turn owner다.
- active plate roles는 terminal-path driven coil-only fields를 갖지 않는다.

## Invariants / fail-fast
- plate roles는 `pcb_total_thickness_mm > copper_thickness_mm > 0`
- active plate roles do not accept `ferrite_set_count`; if present it is an unsupported key and must fail immediately.
- plate `turn_count` realized value는 `>= 2`여야 한다.
- plate `metal_fill_factor` realized value는 `> 0`, `<= 0.6`여야 한다.
- plate `z_usage_ratio` realized value는 `> 0`, `<= 1`이어야 한다.
- plate `y_usage_ratio` realized value는 `> 0`, `<= 1`이어야 한다.
- TX `tx_coil_count` accepts only canonical `[true, 1, 4, 4]` or fixed `[true, n, n, 1]` where `n in 1..4`.
- TX `tx_array_x_usage_ratio` accepts canonical `[false, 0.1, 0.6, 14]` or fixed `[false, r, r, 1]` where `0 < r <= 1`.
- RX `tx_coil_count` and `tx_array_x_usage_ratio` must fail as unsupported.
- old type2 schema id와 removed plate field `shoe_depth_mm`는 즉시 실패한다.
- plate roles에 coil-only keys가 나타나면 즉시 실패한다.
- single-coil usage ratios must realize to `0 < ratio <= 1`; legacy `outer_x_mm`, `outer_y_mm`, and `void_*` fields fail as unsupported public type2 input.
- active example drift는 role/object_id/owner/plane mismatch를 허용하지 않는다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_plate_stack.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]
- [[sdd/code/src/peetsfea/type2_sampled.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- active plate role contract를 legacy single-coil bridge와 다시 결합하지 않는다.
- spec field drift는 sampled/export/import docs와 같이 갱신해야 한다.
- removed plate key는 fallback 없이 unsupported key로 막아야 한다.
