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
- default build path auto-switches plate-stack manifests to import-only AEDT generation
- forced setup-ready runner still rejects unsupported plate roles clearly
- design variable passing and manifest parallelism contracts remain intact

## 변경 시 주의점
- default build auto-switch와 explicit runner override rejection을 같은 behavior로 뭉개지 않는다.
