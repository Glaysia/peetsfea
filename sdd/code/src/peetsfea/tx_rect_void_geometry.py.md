---
title: tx_rect_void_geometry.py
created: 2026-04-17 @ 09:09
updated: 2026-05-03 @ 00:00
tags:
  - tx-rect-void
---

# tx_rect_void_geometry.py

## Source
- Path: `src/peetsfea/tx_rect_void_geometry.py`
- Code note path: `sdd/code/src/peetsfea/tx_rect_void_geometry.py.md`
- Primary graph owner: [type2-rect-void-boundary](../../../architecture/type2-rect-void-boundary.md)

## 역할
- Type2 single-coil blunt corner authoring과 footprint path에 필요한 point/polygon helper와 copper primitive dataclass를 한곳에 모은다.
- joined segment polygon, trace outline polygon, offset-line intersection join point, terminal stub polygon, polygon overlap/simple 검사 같은 pure geometry 규칙을 canonical로 유지한다.
- `tx_rect_void.py`가 export orchestration과 metadata를 맡도록, geometry math와 primitive-level invariants를 분리한다.

## 입력 / 출력
- 입력: 2D centerline points, trace width, polygon tuples, primitive tuples.
- 출력: `RectBounds`, `CopperPrimitive`, joined segment polygon, trace outline polygon, terminal stub polygon, primitive/polygon bounds.

## Canonical state
- module-level mutable state는 없다.
- canonical copper planar owner는 blunt centerline의 per-segment joined polygon이다.
- `trace_outline_polygon()`은 simple polyline 케이스용 단일 폐곡선 helper다. 실제 spiral STEP production path는 현재 segment-face union을 canonical footprint로 사용한다.
- same-corner join의 canonical vertex는 shared centerline node가 아니라 인접 offset line intersection이다.
- debug `boxes`는 이 파일의 소유물이 아니며, 상위 orchestrator가 primitive에서 파생한다.

## Invariants / fail-fast
- centerline segment는 zero-length가 될 수 없다.
- trace width / stub size / extrusion-ready polygon bounds는 항상 양수여야 한다.
- joined segment polygon과 trace outline polygon은 simple polygon이어야 한다.
- polygon overlap helper는 positive-area overlap만 겹침으로 취급해야 한다. edge touch를 overlap으로 넓히면 void validation과 bevel trim이 잘못 흔들린다.
- separate corner join primitive는 canonical path가 아니다. join ownership은 항상 segment polygon 안에 있어야 한다.
- trace width <= 0, centerline segment zero-length, trace outline 단일 폐곡선 조합 실패는 즉시 `ValueError`로 중단한다.

## 직접 의존
- 표준 라이브러리: `math`, `dataclasses`, `typing`

## 이 파일을 쓰는 곳
- [tx_rect_void.py](tx_rect_void.py.md)
- [tx_rect_void_export.py](tx_rect_void_export.py.md)

## 관련 테스트
- `tests/tx_rect_void/test_tx_rect_void.py`

## 변경 시 주의점
- `trace_outline_polygon()`은 `_segment_joined_polygon()`을 제거하지 않고 추가되는 보조 출력이다.
- `_segment_joined_polygon()`의 기존 의미를 유지하고, fallback 없는 fail-fast(예외 즉시 중단) 경로를 준수해야 한다.

## Graph links
- Primary owner: [type2-rect-void-boundary](../../../architecture/type2-rect-void-boundary.md)
- Parent facade: [tx_rect_void.py](tx_rect_void.py.md)
- Centerline collaborator: [tx_rect_void_centerline.py](tx_rect_void_centerline.py.md)
- Export handoff: [tx_rect_void_export.py](tx_rect_void_export.py.md)
- Representative verification: [test_tx_rect_void.py](../../tests/tx_rect_void/test_tx_rect_void.py.md)
