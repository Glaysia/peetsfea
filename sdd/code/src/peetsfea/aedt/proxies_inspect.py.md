---
title: proxies_inspect.py
created: 2026-04-17 @ 09:09
updated: 2026-05-03 @ 00:00
tags:
  - aedt
---

# proxies_inspect.py

## Source
- Path: `src/peetsfea/aedt/proxies_inspect.py`
- Code note path: `sdd/code/src/peetsfea/aedt/proxies_inspect.py.md`
- Status: planned split target; source file is not created yet.
- Primary graph owner: [pyaedt-boundary](../../../../architecture/pyaedt-boundary.md)
- Planning context: `sdd/plans/0.2.22-src-entry-800-line-refactor-threshold.md`

## 역할
- AEDT object/session inspection helper, name extraction, bbox/sample readers, report/setup query helper를 담당한다.

## 입력 / 출력
- 입력: proxy or raw AEDT object/session handles
- 출력: validated inspection values (`name`, `bbox`, edge samples, version env variables, list queries)

## Canonical state
- module-level mutable state는 없다.

## Invariants / fail-fast
- inspect helper도 missing/invalid raw state를 fallback 없이 raise한다.
- inspect helper가 mutation side effect를 가져서는 안 된다.

## 직접 의존
- `sdd/code/src/peetsfea/aedt/proxies_base.py.md`

## 이 파일을 쓰는 곳
- backend inspection/build/import modules
- facade `proxies.py`

## 관련 테스트
- AEDT proxy runtime tests

## 변경 시 주의점
- object inspection helper와 mutation helper를 한 file owner로 되돌리지 않는다.

## Graph links
- Primary owner: [pyaedt-boundary](../../../../architecture/pyaedt-boundary.md)
- Direct handoff: [proxies_base.py](proxies_base.py.md)
