---
title: tx_dd_neo_placement.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - type1
  - aedt
---

# tx_dd_neo_placement.py

## Source
- Path: `src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_placement.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_placement.py.md`
- Status: planned split target; source file is not created yet.
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]

## 역할
- TX DD neo path의 z-anchor, center-y alignment, left-anchor/right-anchor placement translation을 담당한다.

## 입력 / 출력
- 입력: raw path points, resolved board/group placement context
- 출력: board-space placed path points

## Canonical state
- canonical owner는 placed path coordinates이며 downstream builder가 reverse-calculate하지 않는다.

## Invariants / fail-fast
- placement는 deterministic해야 한다.
- anchor math는 board canonical coordinates와 일치해야 한다.

## 직접 의존
- [[sdd/code/src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_path.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_build.py]]
- board-level facade `group_builder_tx_dd_neo.py`

## 관련 테스트
- backend geometry build tests covering TX DD placement symmetry and anchor rules

## 변경 시 주의점
- placement helper가 geometry instantiation side effects를 가지면 안 된다.

## Links
- [[sdd/code/src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_path.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_build.py]]
