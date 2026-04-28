---
title: type2_step_em_input.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - em
  - pyaedt
---

# type2_step_em_input.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_em_input.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_input.py.md`
- Status: active

## 역할
- imported ledger와 setup-ready runtime state에서 EM pipeline input을 조립한다.
- 0.2.24 SDD 기준 active setup mode는 RxOnly다.

## 입력 / 출력
- 입력: imported ownership, RX port metadata, EM policy
- 출력: `EmPipelineInput` equivalent runtime payload

## Canonical state
- RxOnly payload contains RX conductor, RX port, RX source/report context only.
- TX guide objects may be present in imported geometry but are not EM input targets.
- report variable surface is owned by [type2-em-report-contract](../../../../../architecture/type2-em-report-contract.md).

## Invariants / fail-fast
- Missing RX conductor or RX port metadata fails immediately.
- RxOnly must not synthesize TX conductors, TX ports, or TX output variables.
- Imported guide/context bodies are not conductor mesh targets.

## Collaborators
- [type2_step_import_ledger.py](type2_step_import_ledger.py.md)
- [type2_step_port_assignment.py](type2_step_port_assignment.py.md)
- [type2-em-report-contract](../../../../../architecture/type2-em-report-contract.md)
