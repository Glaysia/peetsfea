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
- quarter-turn terminal planner, ring traversal, blunt-corner shaping을 통해 canonical centerline을 만든다.

## 입력 / 출력
- 입력: `RealizedSingleCoilRectVoid`
- 출력: `build_tx_rect_void_centerline()`와 관련 path-planning helper들

## Canonical state
- module-level mutable state는 없다.
- canonical centerline uses one quarter-turn pipeline for partial and full turns: build the axis-aligned skeleton, then apply blunt-corner shaping wherever an internal corner exists.

## Invariants / fail-fast
- canonical terminal ownership comes from realized `terminal_start`, `terminal_end_corner`, fixed `cw` direction, and `turn_qcount`; raw `terminal_path` is not parsed for centerline construction.
- Partial quarter paths are valid: `turn_qcount=1` yields the first side segment, `2` yields a half turn, `3` yields three quarters, and `4n` must match the previous same-corner `n`-turn geometry.
- `turn_qcount=1` has no internal corner and remains straight; `turn_qcount=2` and `3` stay on the outer-ring skeleton and then apply the same blunt-corner processing used by longer paths.
- q < 4 paths do not execute full-turn terminal seeding.
- blunt corner는 45-degree bevel contract를 유지해야 한다.
- full-turn paths keep the previous outer terminal next-ring coordinate seed; shorter partial-quarter paths may terminate at the requested side endpoints because no complete inner ring exists yet.

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
