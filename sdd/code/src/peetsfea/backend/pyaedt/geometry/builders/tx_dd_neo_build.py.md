---
title: tx_dd_neo_build.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - legacy_type1
  - aedt
---

# tx_dd_neo_build.py

## Source
- Path: `src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_build.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_build.py.md`
- Status: planned split target; source file is not created yet.
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]

## 역할
- placed TX DD neo path를 실제 coil geometry, stub source capture, FR4/layer build helper로 변환한다.

## 입력 / 출력
- 입력: placed path points, resolved group/layer context, modeler/session
- 출력: instantiated coil objects, FR4 object, captured stub metadata

## Canonical state
- creation-time coordinates and created object references must remain canonical for downstream use.

## Invariants / fail-fast
- PyAEDT `False` return must raise immediately.
- single/double-layer builder split is explicit and no fallback path exists.

## 직접 의존
- [[sdd/code/src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_path.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_placement.py]]

## 이 파일을 쓰는 곳
- board-level facade `group_builder_tx_dd_neo.py`

## 관련 테스트
- backend geometry build tests for TX DD neo FR4 and stub capture behavior

## 변경 시 주의점
- path planning math와 object creation side effects를 다시 한 module owner로 합치지 않는다.

## Links
- [[sdd/code/src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_path.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/geometry/builders/tx_dd_neo_placement.py]]
