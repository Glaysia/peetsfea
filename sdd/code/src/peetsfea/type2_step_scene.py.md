---
title: type2_step_scene.py
created: 2026-04-17 @ 09:09
updated: 2026-04-19 @ 21:42
tags:
  - step-export
  - scene
---

# type2_step_scene.py

## Source
- Path: `src/peetsfea/type2_step_scene.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_scene.py.md`
- Status: active
- Related feature plans: [[sdd/plans/0.2.24-type2-rx-plate-stack]], [[sdd/plans/0.2.25-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- type2 non-model scene와 modeled scene dispatch를 담당한다.
- active TX/RX plate roles는 shared `type2_plate_stack.py`로 dispatch하고, legacy single-coil roles만 coil builder를 탄다.

## 입력 / 출력
- 입력: parsed type2 spec, owner region specs, seed
- 출력: modeled/non-model scene entries와 canonical coordinates metadata

## Canonical state
- TX plate placement truth는 `tx_region` full `YZ`, `min_x` anchor, `+X` stack다.
- RX plate placement truth는 `rx_region_max` full `YZ`, `min_x` anchor, `+X` stack다.
- active plate roles terminal metadata는 `{"kind": "none"}`다.
- active plate roles는 port-sheet STEP body를 export하지 않는다.

## Invariants / fail-fast
- owner plane and role plane must match
- modeled bounds는 owner bounds를 넘으면 안 된다.
- plate role placement를 centered/rebased placement로 바꾸면 안 된다.
- active plate roles는 coil helper를 호출하면 안 된다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_plate_stack.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- active plate roles에 terminal-path driven sheet reconstruction state를 끌어오지 않는다.
- shared plate-stack placement contract와 import-side owner-fit validation을 같이 유지해야 한다.
