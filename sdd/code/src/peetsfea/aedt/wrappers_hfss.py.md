---
title: wrappers_hfss.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - hfss-import
  - aedt
---

# wrappers_hfss.py

## Source
- Path: `src/peetsfea/aedt/wrappers_hfss.py`
- Code note path: `sdd/code/src/peetsfea/aedt/wrappers_hfss.py.md`
- Status: planned split target; source file is not created yet.
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]

## 역할
- heavy `Modeler3D` and `Hfss` wrapper methods, geometry/session mutation helpers를 담당한다.

## 입력 / 출력
- 입력: raw HFSS/modeler session
- 출력: wrapped high-level AEDT session surface

## Canonical state
- wrapper state is only validated delegation to underlying AEDT session handles.

## Invariants / fail-fast
- mutation-capable wrapper methods must preserve Commandment 1/2 fail-fast semantics
- wrapper methods must not hide raw-session failure through fallback behavior

## 직접 의존
- [[sdd/code/src/peetsfea/aedt/wrappers_common.py]]
- [[sdd/code/src/peetsfea/aedt/wrappers_modules.py]]

## 이 파일을 쓰는 곳
- facade `wrappers.py`
- AEDT-facing backend modules

## 관련 테스트
- AEDT wrapper/proxy runtime tests and backend import/build paths

## 변경 시 주의점
- session mutation helpers와 lightweight module wrappers를 분리 유지한다.

## Links
- [[sdd/code/src/peetsfea/aedt/wrappers_common.py]]
- [[sdd/code/src/peetsfea/aedt/wrappers_modules.py]]
