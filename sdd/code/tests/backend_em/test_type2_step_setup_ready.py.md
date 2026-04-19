---
title: test_type2_step_setup_ready.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 13:46
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
- setup facade enforces exact two-entry tx/rx role pairs before HFSS launch
- mixed role families are rejected fail-fast before runtime attach
- direct mesh helper and direct port assignment accept only exact tx/rx family pairs
- plate-stack fixtures use active `terminal_metadata.kind == "stub_port"` contract from import-pipeline helpers
- plate-stack setup-ready success path asserts full helper chain side effects (mesh, radiation boundary, ports, sources, analysis/report payload, `ValidateDesign`, save, imported-ledger write shape)
- legacy coil full setup path expectations remain intact where still supported

## 변경 시 주의점
- setup facade role-pair gate보다 뒤 단계의 오류를 먼저 기대하는 assertion을 만들지 않는다.
