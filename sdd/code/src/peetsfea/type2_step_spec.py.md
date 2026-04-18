---
title: type2_step_spec.py
created: 2026-04-17 @ 09:09
updated: 2026-04-19 @ 23:58
tags:
  - step-export
  - spec
---

# type2_step_spec.py

## Source
- Path: `src/peetsfea/type2_step_spec.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_spec.py.md`
- Status: active
- Related feature plans: [[sdd/plans/0.2.22-type2-rx-plate-stack-striped-copper]], [[sdd/plans/0.2.22-type2-tx-rx-shared-plate-stack-import-only]], [[sdd/plans/0.2.22-type2-remove-plate-stack-shoe-contract]]

## 역할
- type2 TOML object registry를 typed non-model / modeled spec으로 정규화한다.
- active modeled role set에 `tx_plate_stack`와 `rx_plate_stack`를 포함한 role-aware parser contract를 소유한다.

## 입력 / 출력
- 입력: type2 TOML path
- 출력: parsed type2 step spec, parsed modeled/non-model objects, parsed `outputs`

## Canonical state
- active plate roles는 `tx_plate_stack`와 `rx_plate_stack`다.
- active type2 schema id는 `peetsfea.type2.step.v2`다.
- TX plate object/owner/plane은 `tx_plate_stack` / `tx_region` / `YZ`다.
- RX plate object/owner/plane은 `rx_plate_stack` / `rx_region_max` / `YZ`다.
- plate roles public fields는 `pcb_total_thickness_mm`, `copper_thickness_mm`, `ferrite_set_count`, `turn_count`, `metal_fill_factor`만 가진다.
- plate `turn_count`는 wall-side copper turn owner다.
- active plate roles는 terminal-path driven coil-only fields를 갖지 않는다.

## Invariants / fail-fast
- plate roles는 `pcb_total_thickness_mm > copper_thickness_mm > 0`
- active plate roles는 literal `ferrite_set_count = 10` contract를 유지한다.
- plate `turn_count` realized value는 `>= 2`여야 한다.
- plate `metal_fill_factor` realized value는 `> 0`, `<= 0.5`여야 한다.
- old type2 schema id와 removed plate field `shoe_depth_mm`는 즉시 실패한다.
- plate roles에 coil-only keys가 나타나면 즉시 실패한다.
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
