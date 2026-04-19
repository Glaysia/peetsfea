---
title: test_type2_step_import_pipeline.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 01:35
tags:
  - tests
  - backend-em
  - import-only
---

# test_type2_step_import_pipeline.py

## Source
- Path: `tests/backend_em/test_type2_step_import_pipeline.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_step_import_pipeline.py.md`
- Direct owner: [[sdd/plans/0.2.22-type2-tx-rx-shared-plate-stack-import-only]]
- Direct verification target: [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 역할
- import-only AEDT pipeline의 partition/style/imported-ledger contract를 검증한다.

## Canonical coverage
- active TX/RX plate-stack import succeeds
- exact TX/RX plate body labels are preserved, including explicit copper/pcb/bridge/stub families
- plate-stack exact order keeps the full explicit body list while ferrite-family labels alone follow the merged 3-body contract(`PET/PSA -> ferrite -> air`) with grouped ferrite-family metadata, asymmetric turns, and stub bodies
- plate-stack positive path explicitly verifies merged ferrite-family imported names are exact (`tx_stack_pet_psa/tx_stack_ferrite/tx_stack_air`, `rx_stack_pet_psa/rx_stack_ferrite/rx_stack_air`) and contain no generic `SOLID*` drift
- plate-stack positive path explicitly verifies `g_ferrite_tx` / `g_ferrite_rx` group membership and member order remain intact on import
- plate roles reconstruct `tx_plate_port_sheet` / `rx_plate_port_sheet`
- role-aware owner-fit validation catches bad TX/RX anchors
- imported ledger preserves plate-stack `stub_port` metadata
- TX/RX plate-stack expected-name generation reuses the full explicit export contract and keeps merged exact 3-body names only for ferrite-family labels
- single-coil helper default copper layer position uses `origin_z + 0.4`
- ferrite group contract uses fixed names `g_ferrite_tx` / `g_ferrite_rx` and flattened role-family member order
- active plate-stack import rejects legacy `tx_stack_*_uN` / `rx_stack_*_uN` labels (no fallback)
- active plate-stack import rejects generic `SOLID*` drift for merged ferrite-family labels as export-contract failure (no rename/recovery)

## 변경 시 주의점
- import-only success와 setup-ready failure를 같은 assertion으로 묶지 않는다.
