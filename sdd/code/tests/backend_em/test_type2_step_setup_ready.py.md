---
title: test_type2_step_setup_ready.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 14:08
tags:
  - tests
  - backend-em
  - em
---

# test_type2_step_setup_ready.py

## Source
- Path: `tests/backend_em/test_type2_step_setup_ready.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_step_setup_ready.py.md`
- Direct owner: [[sdd/plans/0.2.22-type2-tx-actual-region-non-model-sampling]]

## 역할
- setup-ready preflight, mesh/port/EM wiring, fail-fast behavior를 검증한다.

## Canonical coverage
- setup facade enforces exact two-entry tx/rx role pairs before HFSS launch
- active RX-only `rx_single_coil` is accepted through full setup-ready
- malformed role sets are rejected fail-fast before runtime attach
- direct mesh helper and direct port assignment accept only exact tx/rx family pairs
- plate-stack fixtures use active `terminal_metadata.kind == "stub_port"` contract from import-pipeline helpers,
  including the left-side `-Y` sheet plane
- plate-stack setup-ready success path은 concrete TX/RX conductor set,
  `g_copper_tx`/`g_copper_rx`, `g_ferrite_tx`/`g_ferrite_rx` 그룹, mesh/port/EM 체인,
  radiation boundary, sources, analysis/report payload, `ValidateDesign`, save, imported-ledger write shape를 함께 검증한다.
- TX array setup-ready coverage must keep one `tx_plate_stack` entry, united `tx_plate_copper`, one TX port, one RX port,
  and the same mesh/source/report contract.
- Mixed-pair coverage must keep TX plate mesh/port semantics and RX `rx_copper_l0` / `rx_port_sheet` semantics together.
- TX array fake HFSS import batches model AEDT solid-only scene import with no connector-sheet reconstruction for new ledgers.
- fake imported non-model batches include concrete `tx_region_actual` member names so setup-ready sees the same non-model scene member set as export/import.
- TX array port-sheet coverage must use branch 0 terminal metadata as one `tx_plate_port_sheet`.
- plate-stack setup-ready failure coverage는 missing concrete conductor,
  missing copper group, missing ferrite group, legacy segment name leakage, SOLID* drift, group-member mismatch를 fail-fast로 요구한다.
- legacy coil full setup path expectations remain intact where still supported

## 변경 시 주의점
- setup facade role-pair gate보다 뒤 단계의 오류를 먼저 기대하는 assertion을 만들지 않는다.
