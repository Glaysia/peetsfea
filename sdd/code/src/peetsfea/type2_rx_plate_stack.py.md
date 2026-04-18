---
title: type2_rx_plate_stack.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 21:40
tags:
  - step-export
  - rx
  - plate-stack
---

# type2_rx_plate_stack.py

## Source
- Path: `src/peetsfea/type2_rx_plate_stack.py`
- Code note path: `sdd/code/src/peetsfea/type2_rx_plate_stack.py.md`
- Status: active transition module
- Related feature plans: [[sdd/plans/0.2.24-type2-rx-plate-stack]], [[sdd/plans/0.2.25-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- RX-only `rx_plate_stack` geometry contract를 처음 도입한 전이 모듈이다.
- 다음 단계에서는 shared `type2_plate_stack.py`가 canonical owner가 되고, 이 note의 파일은 RX compatibility wrapper 또는 thin forwarder 책임으로 축소된다.

## 입력 / 출력
- 입력: `ModeledRxPlateStackSpec`, `rx_region_max` owner spec
- 출력: RX plate-stack scene data 또는 shared plate-stack builder로의 위임 결과

## Canonical state
- RX contract 자체는 유지된다: full `YZ` footprint, `rx_region_max.min_x` anchor, `+X` stack.
- exact body order는 `rx_copper_wall`, `rx_pcb_wall`, `rx_stack_*`, `rx_pcb_coil`, `rx_copper_coil` 34-body contract다.
- terminal metadata는 `{"kind": "none"}` sentinel이다.

## Invariants / fail-fast
- RX contract drift는 shared plate-stack contract drift와 동일하게 취급한다.
- RX-only wrapper가 생기더라도 `tx_rect_void` coil bridge를 다시 호출하면 안 된다.
- shared module 이관 이후에도 legacy centered/rebased placement를 허용하면 안 된다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_plate_stack.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- 이 note의 파일은 최종 canonical geometry owner가 아니다. 실제 계약 변경은 shared plate-stack note와 같이 갱신해야 한다.
