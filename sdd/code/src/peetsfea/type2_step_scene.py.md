---
title: type2_step_scene.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 16:02
tags:
  - type2
  - step-export
---

# type2_step_scene.py

## Source
- Path: `src/peetsfea/type2_step_scene.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_scene.py.md`
- Status: active
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]
- Parent note: [[sdd/code/entry/generate_type2_step.py]]

## 역할
- non-model build123d shapes, single-coil placement offsets, final scene body assembly를 담당한다.
- modeled canonical coordinates/terminal metadata를 geometry에서 직접 계산해 export layer로 전달한다.

## 입력 / 출력
- 입력: parsed type2 specs + owner region specs + seed
- 출력: non-model scene entry/shape tuple, modeled scene child-shapes + modeled scene metadata

## Canonical state
- canonical scene geometry는 single `type2_scene.step` body set이다.
- modeled placement truth는 owner region canonical coordinates에서 derive된 export-time absolute placement다.

## Invariants / fail-fast
- legacy multi-step/object directory outputs는 여기서 다시 만들지 않는다.
- role plane and owner plane must match
- modeled bbox must fit owner bounds before export
- modeled scene child body names must be unique

## 직접 의존
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/tx_rect_void.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/type2_step_export.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- scene assembly와 ledger writing을 다시 결합하지 않는다.
- placement math 변경은 import pipeline owner-fit validation과 함께 갱신해야 한다.

## Links
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]
