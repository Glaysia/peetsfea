---
title: geometry.py
created: 2026-04-20 @ 00:45
updated: 2026-04-20 @ 00:45
tags:
  - types
  - geometry
  - manifest
---

# geometry.py

## Source
- Path: `src/peetsfea/types/geometry.py`
- Code note path: `sdd/code/src/peetsfea/types/geometry.py.md`
- Status: active
- Related feature plan: [[sdd/plans/0.2.22-type2-plate-stack-full-em]]

## 단일 책임
- geometry/endpoint typed-dict contracts를 중앙에서 정의해 runtime/manifest 계층에 공유한다.

## 입력 / 출력
- 입력: 없음 (type declaration module)
- 출력: geometry 관련 `TypedDict`/`Literal` 타입

## Canonical state
- `GroupEndpointEntry.group_kind`는 coil 계열(`tx_dd`, `tx_vertical`, `rx_dd`)과 plate-stack 계열(`tx_plate_stack`, `rx_plate_stack`)을 모두 표현한다.
- endpoint label 타입은 runtime_selection의 `TerminalLabel`을 참조한다.

## Invariants / fail-fast
- 타입 확장은 endpoint semantic을 축소/은닉하지 않는다.
- `group_kind` literal set은 endpoint producer/consumer가 공유하는 canonical contract다.

## Collaborators
- [[sdd/code/src/peetsfea/types/runtime_selection.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_input.py]]
- [[sdd/code/src/peetsfea/types/manifest.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]

## 변경 시 주의점
- `GroupEndpointEntry.group_kind`에서 plate-stack literal을 제거하면 type2 plate-stack EM endpoint contract가 깨진다.
- `CoilPolaritySpec.group_kind`와 endpoint group_kind는 의도적으로 동일하지 않다; polarity spec은 coil-only semantic을 유지한다.
