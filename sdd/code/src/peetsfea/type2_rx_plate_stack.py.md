---
title: type2_rx_plate_stack.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 00:17
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
- Related feature plans: [[sdd/plans/0.2.22-type2-rx-plate-stack]], [[sdd/plans/0.2.22-type2-tx-rx-shared-plate-stack-import-only]], [[sdd/plans/0.2.22-type2-plate-stack-equivalent-3-slab]]

## 역할
- RX compatibility forwarder다.
- geometry/export canonical ownership은 shared `type2_plate_stack.py`만 가진다.
- 이 모듈은 import path 호환을 위해 RX-specific 함수명을 shared owner 호출로만 연결한다.

## 입력 / 출력
- 입력: `ModeledRxPlateStackSpec`, `rx_region_max` owner spec, seed
- 출력: shared plate-stack builder가 만든 RX scene data

## Canonical state
- RX contract 자체는 shared owner state를 그대로 따른다: full `YZ` footprint, `rx_region_max.min_x` anchor, `+X` stack.
- exact body order/group/terminal metadata truth도 shared owner output이 유일한 source다.
- RX ferrite-family thickness policy is inherited from shared owner: public `ferrite_set_count` is absent and the three slabs use fixed equivalent baseline thickness.

## Invariants / fail-fast
- wrapper는 local geometry를 만들지 않는다.
- wrapper는 fallback branch 없이 shared owner 호출 결과를 그대로 반환한다.
- seed는 shared plate-stack sampling contract를 위해 caller가 명시해야 한다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_plate_stack.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- 이 note의 파일은 canonical geometry owner가 아니다. 실제 계약 변경은 shared plate-stack note를 먼저 갱신한다.
- wrapper 함수 시그니처를 바꿀 때는 shared owner 시그니처와 fail-fast semantics를 그대로 유지한다.
