---
title: wrappers_common.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - aedt
---

# wrappers_common.py

## Source
- Path: `src/peetsfea/aedt/wrappers_common.py`
- Code note path: `sdd/code/src/peetsfea/aedt/wrappers_common.py.md`
- Status: planned split target; source file is not created yet.
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]

## 역할
- AEDT wrapper 공통 require helper, shared extraction helper, `_WrappedAccess` base를 담당한다.

## 입력 / 출력
- 입력: raw AEDT/session object
- 출력: validated attr readers and wrapper base helpers

## Canonical state
- module-level mutable state는 없다.

## Invariants / fail-fast
- missing attr/callable/mapping/string/int state는 fallback 없이 즉시 raise

## 직접 의존
- `typing`, `collections.abc`

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/aedt/wrappers_modules.py]]
- [[sdd/code/src/peetsfea/aedt/wrappers_hfss.py]]
- facade `wrappers.py`

## 관련 테스트
- AEDT wrapper/proxy tests and runtime call sites using wrapped sessions

## 변경 시 주의점
- low-level require helper semantics를 완화하면 wrapper layer 전체 fail-fast contract가 무너진다.

## Links
- [[sdd/code/src/peetsfea/aedt/wrappers_modules.py]]
- [[sdd/code/src/peetsfea/aedt/wrappers_hfss.py]]
