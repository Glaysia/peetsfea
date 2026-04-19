---
title: type2_step_scene.py
created: 2026-04-17 @ 09:09
updated: 2026-04-20 @ 04:18
tags:
  - step-export
  - scene
---

# type2_step_scene.py

## Source
- Path: `src/peetsfea/type2_step_scene.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_scene.py.md`
- Status: active
- Primary plan: [[sdd/plans/0.2.22-type2-plate-stack-copper-unite-grouping]]
- Related feature plans: [[sdd/plans/0.2.22-type2-rx-plate-stack-striped-copper]], [[sdd/plans/0.2.22-type2-tx-rx-shared-plate-stack-import-only]]
- Related TX array plan: [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]]

## 역할
- type2 non-model scene와 modeled scene dispatch를 담당한다.
- active TX/RX plate roles는 shared `type2_plate_stack.py`로 seed-aware dispatch하고, legacy single-coil roles만 coil builder를 탄다.

## 입력 / 출력
- 입력: parsed type2 spec, owner region specs, seed
- 출력: modeled/non-model scene entries와 canonical coordinates metadata

## Canonical state
- TX plate placement truth는 `tx_region` full `YZ`, `min_x` anchor, `+X` stack다.
- TX plate array placement truth is delegated to the plate-stack builder/helper and remains a single modeled scene entry.
- RX plate placement truth는 `rx_region_max` full `YZ`, `min_x` anchor, `+X` stack다.
- plate role copper/PCB active height는 owner full `Z` span을 쓴다. `shoe_depth_mm`/shoe fill은 active contract가 아니다.
- active plate roles terminal metadata는 `kind = "stub_port"`다.
- active plate roles는 port-sheet STEP body를 export하지 않는다.
- pre-unite 단계에서는 `*_copper_wall_t*`, `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_in/out` 라벨이 남고,
  final handoff 직전 role당 하나의 united copper 본체를 만든다.
- final handoff 단계의 ferrite 그룹은 role당 정확히 1개 ferrite compound를 만든다:
  TX `g_ferrite_tx`, RX `g_ferrite_rx`.
- final handoff ferrite 그룹은 `*_copper_*`/`*_stub_*` 라벨과 분리되어야 한다.
- RX and TX `tx_coil_count = 1` keep role-level `6` body handoff; TX arrays expand branch-local non-copper
  bodies while keeping one united `tx_plate_copper`.
- final import handoff는 `g_copper_tx`, `g_copper_rx`로부터 concrete conductor members를 재구성하며,
  mesh payload도 conductor-only member set을 사용한다.
- single-coil ferrite family(`tx_wall_*`, `under_rx_*`)도 export 시 같은 ferrite group contract를 따른다.
- final exported copper 그룹은 single/array TX/RX에서 `g_copper_tx -> tx_plate_copper`,
  `g_copper_rx -> rx_plate_copper`로 고정된다.
- TX array branch count must not create extra modeled entries or extra TX port sheets.

## Invariants / fail-fast
- owner plane and role plane must match
- modeled bounds는 owner bounds를 넘으면 안 된다.
- plate role placement를 centered/rebased placement로 바꾸면 안 된다.
- active plate roles는 coil helper를 호출하면 안 된다.
- ferrite group member 순서는 family body 생성 순서와 동일해야 한다.
- active single-branch plate roles는 `expected_exported_body_count = 6`을 스킵하면 안 되고,
  pre-unite label(`*_copper_wall_t*`, `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_in/out`)이 export handoff에 노출되면 안 된다.
- active plate roles는 imported mesh 대상과 final imported body set에 concrete conductor members만 허용한다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_plate_stack.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- active plate roles에 single-coil terminal-path semantics를 끌어오지 않는다.
- shared plate-stack placement contract와 import-side owner-fit validation을 같이 유지해야 한다.
