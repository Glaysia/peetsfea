---
title: type2_modeled_import_adapter.py
created: 2026-04-18 @ 09:09
updated: 2026-05-13 @ 00:00
tags:
  - import
  - pyaedt
---

# type2_modeled_import_adapter.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py.md`
- Status: active
- Primary graph owner: [type2-step-import-boundary](../../../../../architecture/type2-step-import-boundary.md)

## 역할
- Export ledger modeled metadata를 import/setup-ready friendly structure로 변환한다.
- Single-coil terminal metadata parser preserves the `single_coil_port_v1` contract exactly for runtime sheet and port setup.
- `tx_outer_single_coil` modeled entries are rejected by the active import adapter.
- 0.2.24 SDD 기준 RX metadata and RxOnly setup are active.

## 입력 / 출력
- 입력: modeled ledger entries
- 출력: RX modeled import metadata for styling, mesh, and port assignment

## Canonical state
- RX terminal metadata is required for RxOnly port assignment.
- RX/TX single-coil metadata requires global-mm sheet vertices and integration-line endpoints.
- TX terminal metadata names are dormant future two-terminal context only.
- `tx_inner_single_coil` and `rx_single_coil` preserve explicit role/object/terminal metadata for active import/setup paths.

## Invariants / fail-fast
- Missing RX terminal metadata fails immediately.
- RxOnly adapter output must not require TX modeled metadata.
- Unsupported modeled roles, including `tx_outer_single_coil`, fail before imported ledger construction.
- Legacy single-coil terminal metadata without `kind = "single_coil_port_v1"` fails instead of being adapted.

## Graph links
- Primary owner: [type2-step-import-boundary](../../../../../architecture/type2-step-import-boundary.md)
- Direct handoff: [type2_step_import_core.py](type2_step_import_core.py.md)
- Exceptional contract: [type2-em-report-contract](../../../../../architecture/type2-em-report-contract.md)
