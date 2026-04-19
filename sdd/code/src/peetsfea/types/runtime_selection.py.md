---
title: runtime_selection.py
created: 2026-04-20 @ 00:45
updated: 2026-04-20 @ 00:45
tags:
  - types
  - runtime
  - selection
---

# runtime_selection.py

## Source
- Path: `src/peetsfea/types/runtime_selection.py`
- Code note path: `sdd/code/src/peetsfea/types/runtime_selection.py.md`
- Status: active
- Related feature plan: [[sdd/plans/0.2.22-type2-plate-stack-full-em]]

## 단일 책임
- runtime selected-parameter 및 selection/terminal label 타입을 canonical typed contract로 제공한다.

## 입력 / 출력
- 입력: 없음 (type declaration module)
- 출력: runtime selection `TypedDict`/`Literal` 타입

## Canonical state
- `TerminalLabel`은 coil corner label(`A/B/C/D/a/b/c/d`)과 plate-stack stub label(`input_stub`, `output_stub`)을 함께 수용한다.
- 기존 coil label domain은 유지되며, plate-stack extension만 추가된다.

## Invariants / fail-fast
- terminal label literal domain은 endpoint 생성/검증 계층에서 shared contract로 사용된다.
- plate-stack endpoint label을 임시 문자열로 우회하지 않고 `TerminalLabel` literal에 명시한다.

## Collaborators
- [[sdd/code/src/peetsfea/types/geometry.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_input.py]]
- [[sdd/code/src/peetsfea/types/manifest.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]

## 변경 시 주의점
- `TerminalLabel`에서 stub label을 제거하면 plate-stack endpoint typing이 깨진다.
- coil parsing/validation 코드가 기대하는 기존 8개 label은 그대로 허용되어야 한다.
