---
title: proxies_base.py
created: 2026-04-17 @ 09:09
updated: 2026-05-03 @ 00:00
tags:
  - aedt
---

# proxies_base.py

## Source
- Path: `src/peetsfea/aedt/proxies_base.py`
- Code note path: `sdd/code/src/peetsfea/aedt/proxies_base.py.md`
- Status: planned split target; source file is not created yet.
- Primary graph owner: [pyaedt-boundary](../../../../architecture/pyaedt-boundary.md)
- Planning context: `sdd/plans/0.2.22-src-entry-800-line-refactor-threshold.md`

## 역할
- proxy base class, require helpers, concrete proxy classes, wrap/unwrap primitive helpers를 담당한다.

## 입력 / 출력
- 입력: raw AEDT session/object handles
- 출력: proxy instances and stable wrap/unwrap API

## Canonical state
- module-level mutable state는 없다.
- canonical proxy identity는 wrapped raw object reference다.

## Invariants / fail-fast
- missing required attributes raise immediately
- wrap/unwrap path is explicit; default/fallback object coercion is forbidden

## 직접 의존
- `typing`, `collections.abc`

## 이 파일을 쓰는 곳
- `sdd/code/src/peetsfea/aedt/proxies_ops.py.md`
- `sdd/code/src/peetsfea/aedt/proxies_inspect.py.md`
- facade `proxies.py`

## 관련 테스트
- AEDT proxy runtime tests

## 변경 시 주의점
- proxy class definitions와 heavy AEDT operation helpers를 다시 한 file에 합치지 않는다.

## Graph links
- Primary owner: [pyaedt-boundary](../../../../architecture/pyaedt-boundary.md)
- Direct handoff: [proxies_ops.py](proxies_ops.py.md)
- Direct handoff: [proxies_inspect.py](proxies_inspect.py.md)
