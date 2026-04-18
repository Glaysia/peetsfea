---
title: test_type2_modeled_import_adapter.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 21:47
tags:
  - tests
  - backend-em
  - import-only
---

# test_type2_modeled_import_adapter.py

## Source
- Path: `tests/backend_em/test_type2_modeled_import_adapter.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_modeled_import_adapter.py.md`

## 역할
- modeled import adapter가 coil metadata와 plate sentinel metadata를 role-aware로 파싱하는지 검증한다.

## Canonical coverage
- `tx_plate_stack` / `rx_plate_stack` accept `{"kind": "none"}`
- coil roles still require full terminal metadata
- malformed sentinel or mixed role metadata is rejected

## 변경 시 주의점
- geometry-only role rejection expectation을 import-only acceptance expectation으로 갱신해야 한다.
