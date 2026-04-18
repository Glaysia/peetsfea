---
title: type2_plate_stack.py
created: 2026-04-19 @ 21:42
updated: 2026-04-19 @ 21:42
tags:
  - step-export
  - tx
  - rx
  - plate-stack
---

# type2_plate_stack.py

## Source
- Path: `src/peetsfea/type2_plate_stack.py`
- Code note path: `sdd/code/src/peetsfea/type2_plate_stack.py.md`
- Status: planned active
- Related feature plan: [[sdd/plans/0.2.25-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- active TX/RX plate-stack geometry contract의 canonical owner다.
- role config 차이만으로 TX `tx_plate_stack`와 RX `rx_plate_stack` scene data를 모두 만든다.

## 입력 / 출력
- 입력: plate-stack modeled spec, placement owner spec
- 출력: labeled solids, canonical coordinates, `terminal_metadata = {"kind": "none"}`를 포함한 modeled scene data

## Canonical state
- TX는 `tx_region` full `YZ`, `min_x` anchor, `+X` stack를 사용한다.
- RX는 `rx_region_max` full `YZ`, `min_x` anchor, `+X` stack를 사용한다.
- 두 role 모두 PCB 2장과 literal `ferrite / pet_psa / air` 10 sets를 exact body order로 export한다.

## Invariants / fail-fast
- `pcb_total_thickness_mm > copper_thickness_mm > 0`
- total thickness는 owner thickness budget 안에 들어가야 한다.
- body labels는 unique하고 exact-name order contract를 유지해야 한다.
- coil-only field semantics는 여기로 들어오면 안 된다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]
- [[sdd/code/src/peetsfea/type2_rx_plate_stack.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- shared module이 active contract owner이므로 TX/RX drift를 role별 helper에 따로 분기해 쌓지 않는다.
- import-side body-name partition/style contract와 exact order를 같이 갱신해야 한다.
