---
title: test_build_type2_entry.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 21:47
tags:
  - tests
  - type2
  - build
---

# test_build_type2_entry.py

## Source
- Path: `tests/type2/test_build_type2_entry.py`
- Code note path: `sdd/code/tests/type2/test_build_type2_entry.py.md`

## 역할
- build entry/runtime wiring과 manifest-driven runner behavior를 검증한다.

## Canonical coverage
- active plate-stack manifest can still export missing STEP
- active plate-stack build path does not auto-switch to import-only
- setup-ready runner unsupported error surfaces clearly
- design variable passing and manifest parallelism contracts remain intact

## 변경 시 주의점
- geometry-view import-only policy를 build success expectation으로 바꾸지 않는다.
