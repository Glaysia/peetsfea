---
title: type2_rx_plate_stack.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 17:35
tags:
  - step-export
  - rx
  - plate-stack
---

# type2_rx_plate_stack.py

## Source
- Path: `src/peetsfea/type2_rx_plate_stack.py`
- Code note path: `sdd/code/src/peetsfea/type2_rx_plate_stack.py.md`
- Status: active
- Related feature plan: [[sdd/plans/0.2.24-type2-rx-plate-stack]]
- Parent note: [[sdd/code/entry/generate_type2_step.py]]

## 역할
- geometry-only `rx_plate_stack` modeled role의 build123d solid taxonomy와 export metadata를 전담한다.
- `rx_region_max` full `YZ` footprint를 source of truth로 사용해 literal ferrite/PET/air set과 wall/coil-side PCB+copper solids를 만든다.

## 입력 / 출력
- 입력: parsed `ModeledRxPlateStackSpec`, `rx_region_max` non-model owner spec
- 출력: labeled solid tuple, modeled scene metadata

## Canonical state
- RX plate stack exact body order는 `rx_copper_wall`, `rx_pcb_wall`, `rx_stack_ferrite_u*`, `rx_stack_pet_psa_u*`, `rx_stack_air_u*`, `rx_pcb_coil`, `rx_copper_coil`이다.
- canonical bounds는 exported solids union이고 frame origin은 owner `rx_region_max.min_x/min_y/min_z`다.
- terminal metadata는 geometry-only sentinel `{"kind": "none"}`만 가진다.

## Invariants / fail-fast
- `pcb_total_thickness_mm > copper_thickness_mm > 0`
- `ferrite_set_count >= 1`
- total stack thickness must fit inside `rx_region_max.size_x`
- body labels are unique and `<= 32` chars

## 직접 의존
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/type2_step_scene.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- `tx_rect_void` geometry/render bridge를 여기서 호출하지 않는다.
- RX footprint source를 coil bounds나 centered placement로 되돌리지 않는다.
