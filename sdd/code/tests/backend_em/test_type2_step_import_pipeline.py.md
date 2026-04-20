---
title: test_type2_step_import_pipeline.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 14:08
tags:
  - tests
  - backend-em
  - import-only
---

# test_type2_step_import_pipeline.py

## Source
- Path: `tests/backend_em/test_type2_step_import_pipeline.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_step_import_pipeline.py.md`
- Direct owner: [[sdd/plans/0.2.22-type2-tx-rx-shared-plate-stack-import-only]], [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]], [[sdd/plans/0.2.22-type2-tx-actual-region-non-model-sampling]]
- Direct verification target: [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 역할
- import-only AEDT pipeline의 partition/style/imported-ledger contract를 검증한다.

## Canonical coverage
- active TX/RX plate-stack import succeeds
- exact TX/RX plate body labels are preserved as export-side provenance
- plate-stack exact order keeps the full explicit body list while final imported conductor members remain concrete export
  members: TX/RX use `tx_plate_copper`/`rx_plate_copper` for single and array cases.
  Ferrite-family labels follow the direct equivalent 3-slab contract(`PET/PSA -> ferrite -> air`) with grouped ferrite-family metadata, asymmetric turns, and stub bodies.
- plate-stack positive path explicitly verifies merged ferrite-family imported names are exact (`tx_stack_pet_psa/tx_stack_ferrite/tx_stack_air`, `rx_stack_pet_psa/rx_stack_ferrite/rx_stack_air`) and contain no generic `SOLID*` drift
- plate-stack positive path explicitly verifies copper 그룹(`g_copper_tx`, `g_copper_rx`)이 concrete conductor members를 포함하고
  `g_ferrite_tx` / `g_ferrite_rx` group membership/member order가 온전히 유지되는지 확인한다.
- TX array import coverage must accept branch-local TX PCB/ferrite-family bodies and a united `tx_plate_copper` under
  one `tx_plate_stack` entry.
- TX array import coverage must not reconstruct connector sheet conductors for newly generated ledgers.
- plate-stack export contract 실패 회귀로 `g_copper_tx`/`g_copper_rx` 또는 `g_ferrite_tx`/`g_ferrite_rx` 하나라도 누락될 경우
  import가 즉시 실패해야 함을 보장한다.
- plate roles reconstruct `tx_plate_port_sheet` / `rx_plate_port_sheet`
- plate-stack `stub_port` fixture metadata uses the left-side `-Y` sheet plane, matching generated STEP ledger coordinates.
- role-aware owner-fit validation catches bad TX/RX anchors
- imported ledger preserves plate-stack `stub_port` metadata
- TX/RX plate-stack expected-name generation reuses the full explicit export contract for provenance while requiring final
  plate-stack imported conductors to be the concrete exported copper members.
- single-coil helper default copper layer position uses `origin_z + 0.4`
- ferrite group contract uses fixed names `g_ferrite_tx` / `g_ferrite_rx` and flattened role-family member order
- active plate-stack import rejects legacy `tx_stack_*_uN` / `rx_stack_*_uN` labels (no fallback)
- active plate-stack import rejects generic `SOLID*` drift for merged ferrite-family labels as export-contract failure (no rename/recovery)
- active plate-stack import은 legacy final segment names(`*_copper_wall_t*`, `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_*`)를 final copper body로 인정하지 않고 즉시 실패한다.
- active plate-stack import은 legacy segment-export 케이스(`*_stack_*_uN`)와
  `tx_plate_copper`/`rx_plate_copper` 미생성 케이스를 future regression으로 추가 추적한다.
- active plate-stack import accepts partial-Z active windows from `z_usage_ratio` only when TX remains max-Z anchored and RX remains min-Z anchored.
- active plate-stack import accepts partial-Y active windows from `y_usage_ratio` when the modeled bounds encode a global `Y=0`
  centered active span plus the fixed `-Y` stub overhang.
- active plate-stack import rejects Y bounds that fit inside the owner but are off the global centered active-window contract.
- TX array import must not create extra modeled entries or per-branch port sheets.
- Non-model import fixtures include concrete `tx_region_actual` member names between `tx_region` and `rx_region_max`; multi-tile tests use `tx_region_actual_x{xi}_y{yi}` names.

## 변경 시 주의점
- import-only success와 setup-ready failure를 같은 assertion으로 묶지 않는다.
