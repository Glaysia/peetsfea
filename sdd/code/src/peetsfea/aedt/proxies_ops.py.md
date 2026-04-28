---
title: proxies_ops.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - aedt
---

# proxies_ops.py

## Source
- Path: `src/peetsfea/aedt/proxies_ops.py`
- Code note path: `sdd/code/src/peetsfea/aedt/proxies_ops.py.md`
- Status: planned split target; source file is not created yet.
- Related plan: [0.2.22-src-entry-800-line-refactor-threshold](../../../../plans/0.2.22-src-entry-800-line-refactor-threshold.md)

## 역할
- wrapped/raw AEDT session에 대한 mutation-capable operation helper를 담당한다.

## 입력 / 출력
- 입력: proxy or raw session handles, validated operation payload
- 출력: created/modified AEDT objects and fail-fast side effects

## Canonical state
- module-level mutable state는 없다.

## Invariants / fail-fast
- operation helper는 PyAEDT `False`를 즉시 raise로 전환해야 한다.
- proxy unwrap/wrap 경계는 explicit해야 한다.

## 직접 의존
- [proxies_base.py](proxies_base.py.md)

## 이 파일을 쓰는 곳
- backend geometry/build/import modules
- facade `proxies.py`

## 관련 테스트
- AEDT proxy runtime tests

## 변경 시 주의점
- inspect-only helpers와 mutation helpers를 분리 유지한다.
- payload normalization을 fallback-style permissive parser로 바꾸지 않는다.

## Links
- [proxies_base.py](proxies_base.py.md)
- [proxies_inspect.py](proxies_inspect.py.md)
