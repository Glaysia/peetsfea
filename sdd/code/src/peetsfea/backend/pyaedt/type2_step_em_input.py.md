---
title: type2_step_em_input.py
created: 2026-04-18 @ 09:09
updated: 2026-05-13 @ 00:00
tags:
  - em
  - pyaedt
---

# type2_step_em_input.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_em_input.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_input.py.md`
- Status: active
- Primary graph owner: [type2-em-setup-boundary](../../../../../architecture/type2-em-setup-boundary.md)

## 역할
- imported ledger와 setup-ready runtime state에서 EM pipeline input을 조립한다.
- Single-coil port endpoints use `integration_line_start_xyz` and `integration_line_end_xyz` from the ledger contract.
- 0.2.24 SDD 기준 active setup modes are `RxOnly` and `TxRx`.
- `TxRx` payloads include `tx_inner_single_coil` and RX terminal paths so source/report setup can bind `TX_TML` and `RX_TML`.
- `tx_inner_single_coil` is now resolved through deterministic imported-name families (`tx_inner_pcb_l*`, `tx_inner_copper_l*`), not generic TX roles.

## 입력 / 출력
- 입력: imported ownership, TX inner/RX port metadata, EM policy
- 출력: mode-specific `EmPipelineInput` equivalent runtime payload

## Canonical state
- RxOnly payload contains RX conductor, RX port, RX source/report context only.
- TX guide objects may be present in imported geometry but are not EM input targets.
- report variable surface is owned by `sdd/architecture/type2-em-report-contract.md`.

## Invariants / fail-fast
- Missing RX/TX conductor or terminal metadata fails immediately with role context.
- Single-coil endpoint coordinates must not be reconstructed from plane points plus sheet vertex coordinates.
- Unsupported role families or unexpected role pairings fail immediately with role names.
- RxOnly must not synthesize TX conductors, TX ports, or TX output variables.
- Imported guide/context bodies are not conductor mesh targets.

## Graph links
- Primary owner: [type2-em-setup-boundary](../../../../../architecture/type2-em-setup-boundary.md)
- Direct handoff: [type2_step_port_assignment.py](type2_step_port_assignment.py.md)
- Exceptional artifact handoff: [type2_step_import_ledger.py](type2_step_import_ledger.py.md)
- Exceptional contract: [type2-em-report-contract](../../../../../architecture/type2-em-report-contract.md)
- Related plan: [0.2.25 Type2 Port Sheet Contract Rewrite](../../../../../plans/0.2.25-type2-port-sheet-contract-rewrite.md)
