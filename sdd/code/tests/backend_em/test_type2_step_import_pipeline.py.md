---
title: test_type2_step_import_pipeline.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 21:47
tags:
  - tests
  - backend-em
  - import-only
---

# test_type2_step_import_pipeline.py

## Source
- Path: `tests/backend_em/test_type2_step_import_pipeline.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_step_import_pipeline.py.md`

## 역할
- import-only AEDT pipeline의 partition/style/imported-ledger contract를 검증한다.

## Canonical coverage
- active TX/RX plate-stack import succeeds
- exact TX/RX plate body labels are preserved
- plate roles skip port-sheet reconstruction
- role-aware owner-fit validation catches bad TX/RX anchors

## 변경 시 주의점
- import-only success와 setup-ready failure를 같은 assertion으로 묶지 않는다.
