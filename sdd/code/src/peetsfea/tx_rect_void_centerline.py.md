---
title: tx_rect_void_centerline.py
created: 2026-04-17 @ 09:09
updated: 2026-05-03 @ 00:00
tags:
  - tx-rect-void
---

# tx_rect_void_centerline.py

## Source
- Path: `src/peetsfea/tx_rect_void_centerline.py`
- Code note path: `sdd/code/src/peetsfea/tx_rect_void_centerline.py.md`
- Status: planned split target; source file is not created yet.
- Primary graph owner: [type2-rect-void-boundary](../../../architecture/type2-rect-void-boundary.md)

## 역할
- same-corner terminal planner, ring traversal, blunt-corner shaping을 통해 canonical centerline을 만든다.

## 입력 / 출력
- 입력: `RealizedSingleCoilRectVoid`
- 출력: `build_tx_rect_void_centerline()`와 관련 path-planning helper들

## Canonical state
- module-level mutable state는 없다.
- canonical centerline은 sharp seed path가 아니라 blunt corner가 적용된 point sequence다.

## Invariants / fail-fast
- same-corner seed ownership은 type1-derived contract를 유지해야 한다.
- blunt corner는 45-degree bevel contract를 유지해야 한다.
- outer terminal은 next-ring coordinate seed를 유지해야 하며 raw corner에 남으면 안 된다.

## 직접 의존
- [tx_rect_void_types.py](tx_rect_void_types.py.md)

## 이 파일을 쓰는 곳
- [tx_rect_void_export.py](tx_rect_void_export.py.md)
- compatibility facade `tx_rect_void.py`

## 관련 테스트
- `tests/tx_rect_void/test_tx_rect_void.py`

## 변경 시 주의점
- centerline ownership과 geometry ownership을 섞지 않는다. 이 파일은 path만 소유하고 solid authoring은 소유하지 않는다.
- point semantics를 바꾸면 terminal metadata와 short-detection tests가 모두 바뀐다.

## Graph links
- Primary owner: [type2-rect-void-boundary](../../../architecture/type2-rect-void-boundary.md)
- Parent facade: [tx_rect_void.py](tx_rect_void.py.md)
- Direct input contract: [tx_rect_void_spec.py](tx_rect_void_spec.py.md)
- Export handoff: [tx_rect_void_export.py](tx_rect_void_export.py.md)
- Geometry collaborator: [tx_rect_void_geometry.py](tx_rect_void_geometry.py.md)
