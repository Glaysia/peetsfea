---
title: type2_step_import_partition.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 21:45
tags:
  - hfss-import
  - partition
---

# type2_step_import_partition.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_partition.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py.md`
- Status: active
- Related feature plan: [[sdd/plans/0.2.25-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- imported HFSS object names를 modeled/non-model ownership과 body-material families로 partition한다.

## 입력 / 출력
- 입력: validated step ledger, imported object names
- 출력: modeled object id별 imported names, non-model object id별 imported names, body-role grouping

## Canonical state
- TX plate families는 `tx_copper_wall`, `tx_pcb_wall`, `tx_stack_*`, `tx_pcb_coil`, `tx_copper_coil`를 분류한다.
- RX plate families는 `rx_copper_wall`, `rx_pcb_wall`, `rx_stack_*`, `rx_pcb_coil`, `rx_copper_coil`를 분류한다.
- imported exact-name contract는 export ledger order와 동일한 label set을 요구한다.

## Invariants / fail-fast
- modeled exact-name drift와 unclaimed imported object는 hard failure다.
- tri-layer ferrite/PET/air body counts는 서로 맞아야 한다.
- plate role body partition은 copper/pcb가 각각 2장 계약을 유지해야 한다.

## Collaborators
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 변경 시 주의점
- legacy coil naming family와 plate-stack naming family를 같은 prefix 규칙으로 뭉개지 않는다.
