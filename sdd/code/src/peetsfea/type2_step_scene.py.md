---
title: type2_step_scene.py
created: 2026-04-17 @ 09:09
updated: 2026-04-19 @ 23:59
tags:
  - step-export
  - scene
---

# type2_step_scene.py

## Source
- Path: `src/peetsfea/type2_step_scene.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_scene.py.md`
- Status: active
- Related feature plans: [[sdd/plans/0.2.22-type2-rx-plate-stack-striped-copper]], [[sdd/plans/0.2.22-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- type2 non-model scene와 modeled scene dispatch를 담당한다.
- active TX/RX plate roles는 shared `type2_plate_stack.py`로 seed-aware dispatch하고, legacy single-coil roles만 coil builder를 탄다.

## 입력 / 출력
- 입력: parsed type2 spec, owner region specs, seed
- 출력: modeled/non-model scene entries와 canonical coordinates metadata

## Canonical state
- TX plate placement truth는 `tx_region` full `YZ`, `min_x` anchor, `+X` stack다.
- RX plate placement truth는 `rx_region_max` full `YZ`, `min_x` anchor, `+X` stack다.
- plate role copper/PCB active height는 `shoe_depth_mm`가 제거한 active span을 쓰고, cutout은 shoe fill이 메운다.
- active plate roles terminal metadata는 `kind = "stub_port"`다.
- active plate roles는 port-sheet STEP body를 export하지 않는다.
- ferrite family가 scene에 export될 때 role당 정확히 1개 ferrite compound를 만든다:
  TX `g_ferrite_tx`, RX `g_ferrite_rx`.
- single-coil ferrite family(`tx_wall_*`, `under_rx_*`)도 export 시 같은 ferrite group contract를 따른다.

## Invariants / fail-fast
- owner plane and role plane must match
- modeled bounds는 owner bounds를 넘으면 안 된다.
- plate role placement를 centered/rebased placement로 바꾸면 안 된다.
- active plate roles는 coil helper를 호출하면 안 된다.
- ferrite group member 순서는 family body 생성 순서와 동일해야 한다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_plate_stack.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- active plate roles에 single-coil terminal-path semantics를 끌어오지 않는다.
- shared plate-stack placement contract와 import-side owner-fit validation을 같이 유지해야 한다.
