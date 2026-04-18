---
title: wrappers_modules.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - aedt
---

# wrappers_modules.py

## Source
- Path: `src/peetsfea/aedt/wrappers_modules.py`
- Code note path: `sdd/code/src/peetsfea/aedt/wrappers_modules.py.md`
- Status: planned split target; source file is not created yet.
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]

## 역할
- lightweight AEDT module wrappers (`Object3d`, `BoundaryModule`, `Desktop`, `Materials`, `Design`, setup/report/solutions modules)를 담당한다.

## 입력 / 출력
- 입력: raw PyAEDT module/object handles
- 출력: wrapped module/object API with explicit validated access

## Canonical state
- wrapper object owns only validated access surface, not repository runtime geometry state.

## Invariants / fail-fast
- attr access and return-shape validation remain explicit
- generic silent fallback to raw object access is forbidden

## 직접 의존
- [[sdd/code/src/peetsfea/aedt/wrappers_common.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/aedt/wrappers_hfss.py]]
- facade `wrappers.py`

## 관련 테스트
- AEDT wrapper/proxy runtime tests

## 변경 시 주의점
- lightweight wrappers와 heavy `Hfss`/`Modeler3D` wrapper methods를 다시 한 file에 모으지 않는다.

## Links
- [[sdd/code/src/peetsfea/aedt/wrappers_common.py]]
- [[sdd/code/src/peetsfea/aedt/wrappers_hfss.py]]
