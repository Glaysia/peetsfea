---
title: test_type2_step_import_pipeline.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 00:45
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
- plate-stack exact order follows the interleaved `PET/PSA -> ferrite -> air` body contract, with grouped ferrite-family metadata, asymmetric turns, and stub bodies
- plate roles reconstruct `tx_plate_port_sheet` / `rx_plate_port_sheet`
- role-aware owner-fit validation catches bad TX/RX anchors
- imported ledger preserves plate-stack `stub_port` metadata
- TX/RX plate-stack expected-name generation uses a shared `pcb_total_thickness_mm = 0.4` baseline to resist drift
- single-coil helper default copper layer position uses `origin_z + 0.4`
- ferrite group contract uses fixed names `g_ferrite_tx` / `g_ferrite_rx` and flattened role-family member order

## 변경 시 주의점
- import-only success와 setup-ready failure를 같은 assertion으로 묶지 않는다.
