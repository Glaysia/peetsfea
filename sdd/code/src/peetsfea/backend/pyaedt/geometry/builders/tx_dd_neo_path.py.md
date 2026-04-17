---
title: tx_dd_neo_path.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - type1
  - aedt
---

# tx_dd_neo_path.py

## Source
- Path: `src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_path.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_path.py.md`
- Status: planned split target; source file is not created yet.
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]

## 역할
- neo TX DD terminal-path contract parsing, ring traversal, same-corner seed path generation을 담당한다.

## 입력 / 출력
- 입력: resolved coil group geometry, terminal path contract, layer geometry scalars
- 출력: canonical polyline points before placement

## Canonical state
- module-level mutable state는 없다.
- canonical owner는 placement 이전의 TX DD path point sequence다.

## Invariants / fail-fast
- axis-aligned path contract 유지
- same-corner contract 위반은 즉시 raise
- direction/corner label parsing은 explicit set만 허용

## 직접 의존
- builder-local geometry types

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_placement.py]]
- board-level facade `group_builder_tx_dd_neo.py`

## 관련 테스트
- backend geometry build tests around TX DD neo path generation

## 변경 시 주의점
- path generation과 placement translation을 다시 결합하지 않는다.

## Links
- [[sdd/code/src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_placement.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_build.py]]
