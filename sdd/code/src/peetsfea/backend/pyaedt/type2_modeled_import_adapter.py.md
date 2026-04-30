---
title: type2_modeled_import_adapter.py
created: 2026-04-18 @ 09:09
updated: 2026-04-30 @ 00:00
tags:
  - import
  - pyaedt
---

# type2_modeled_import_adapter.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py.md`
- Status: active

## 역할
- Export ledger modeled metadata를 import/setup-ready friendly structure로 변환한다.
- `tx_outer_single_coil` modeled entries are accepted as geometry-only single-coil import metadata.
- 0.2.24 SDD 기준 RX metadata and RxOnly setup are active.

## 입력 / 출력
- 입력: modeled ledger entries
- 출력: RX modeled import metadata for styling, mesh, and port assignment

## Canonical state
- RX terminal metadata is required for RxOnly port assignment.
- TX terminal metadata names are dormant future two-terminal context only.
- `tx_outer_single_coil` preserves its explicit role/object/terminal metadata without enabling a TX outer port/source/report contract.

## Invariants / fail-fast
- Missing RX terminal metadata fails immediately.
- RxOnly adapter output must not require TX modeled metadata.
- Unsupported modeled roles fail before imported ledger construction; the supported role literal list includes `tx_outer_single_coil`.

## Collaborators
- [type2_step_import_core.py](type2_step_import_core.py.md)
- [type2-em-report-contract](../../../../../architecture/type2-em-report-contract.md)
