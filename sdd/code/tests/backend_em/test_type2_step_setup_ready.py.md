---
title: test_type2_step_setup_ready.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 21:47
tags:
  - tests
  - backend-em
  - em
---

# test_type2_step_setup_ready.py

## Source
- Path: `tests/backend_em/test_type2_step_setup_ready.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_step_setup_ready.py.md`

## 역할
- setup-ready preflight, mesh/port/EM wiring, fail-fast behavior를 검증한다.

## Canonical coverage
- active plate roles are rejected before HFSS launch
- direct mesh/port/EM helpers also reject plate roles
- legacy coil path expectations remain intact where still supported

## 변경 시 주의점
- active plate roles를 partial setup-ready support로 넓히지 않는다.
