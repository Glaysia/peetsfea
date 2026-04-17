---
title: tx_rect_void_geometry.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - type2
  - tx-rect-void
---

# tx_rect_void_geometry.py

## Source
- Path: `src/peetsfea/tx_rect_void_geometry.py`
- Code note path: `sdd/code/src/peetsfea/tx_rect_void_geometry.py.md`
- Parent orchestrator: [[sdd/code/src/peetsfea/tx_rect_void.py]]
- Related plan: [[sdd/plans/0.2.22-type2-single-coil-corner-relief]]
- Related tests: [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py]]

## 역할
- Type2 single-coil blunt corner authoring에 필요한 point/polygon helper와 copper primitive dataclass를 한곳에 모은다.
- joined segment polygon, offset-line intersection join point, terminal stub polygon, polygon overlap/simple 검사 같은 pure geometry 규칙을 canonical로 유지한다.
- `tx_rect_void.py`가 export orchestration과 metadata를 맡도록, geometry math와 primitive-level invariants를 분리한다.

## 입력 / 출력
- 입력: 2D centerline points, trace width, polygon tuples, primitive tuples.
- 출력: `RectBounds`, `CopperPrimitive`, joined segment polygon, terminal stub polygon, primitive/polygon bounds.

## Canonical state
- module-level mutable state는 없다.
- canonical copper planar owner는 blunt centerline의 per-segment joined polygon이다.
- same-corner join의 canonical vertex는 shared centerline node가 아니라 인접 offset line intersection이다.
- debug `boxes`는 이 파일의 소유물이 아니며, 상위 orchestrator가 primitive에서 파생한다.

## Invariants / fail-fast
- centerline segment는 zero-length가 될 수 없다.
- trace width / stub size / extrusion-ready polygon bounds는 항상 양수여야 한다.
- joined segment polygon은 simple polygon이어야 한다.
- polygon overlap helper는 positive-area overlap만 겹침으로 취급해야 한다. edge touch를 overlap으로 넓히면 void validation과 bevel trim이 잘못 흔들린다.
- separate corner join primitive는 canonical path가 아니다. join ownership은 항상 segment polygon 안에 있어야 한다.

## 직접 의존
- 표준 라이브러리: `math`, `dataclasses`, `typing`

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/tx_rect_void.py]]

## 관련 테스트
- [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py]]

## 변경 시 주의점
- joined segment polygon과 overlap helper의 semantics를 바꾸면 blunt corner geometry가 다시 “centerline point join”으로 퇴행할 수 있다.
- 여기서 edge-touch / overlap 판정을 바꾸면 `_apply_blunt_corner_to_polyline()`의 trim 결과와 final void validation이 동시에 달라진다.
