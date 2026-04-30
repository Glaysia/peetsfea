---
title: type2_step_setup_ready.py
created: 2026-04-18 @ 09:09
updated: 2026-04-29 @ 00:00
tags:
  - em
  - pyaedt
---

# type2_step_setup_ready.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_setup_ready.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py.md`
- Status: active

## 역할
- STEP import 후 setup-ready HFSS project를 만든다.
- 0.2.24 SDD 기준 active modes are `RxOnly` and `TxRx`.
- `TxRx` orchestration preserves `tx_inner_single_coil` and RX ledger entries and passes both into import styling, port assignment, EM input, post-import mesh, and report setup.

## Canonical state
- RxOnly creates RX mesh, radiation boundary, one RX port, RX sources/reports, validates, and saves.
- TxRx creates TX inner + RX mesh, radiation boundary, TX/RX ports, two-terminal sources/reports, validates, and saves.
- The solve-enabled facade keeps the same HFSS session alive after setup-ready generation, runs `Setup1`, exports the active report CSV, then saves.
- Generic TX roles remain unsupported setup targets.
- The full imported ledger records all imported bodies; active setup resolves and caches a branch-specific modeled ledger for mesh, port assignment, EM input, sources, and reports.
- `RxOnly` branch accepts only a single `rx_single_coil` modeled object.
- `TxRx` branch uses exact `tx_inner_single_coil` + `rx_single_coil` modeled objects and preserves both for downstream passes.
- Report variables are owned by [type2-em-report-contract](../../../../../architecture/type2-em-report-contract.md).

## Invariants / fail-fast
- PyAEDT false returns fail immediately.
- RxOnly must not create TX ports or TX output variables.
- `TxRx` must create TX and RX ports, TX+RX output variables, and two terminal groups.
- Generic TX roles are rejected before setup-ready begins; there is no paired-mode fallback path.
- A loaded ledger with exactly one `tx_inner_single_coil` and one `rx_single_coil` in `TxRx` mode is preserved through setup as both active modeled entries.
- RxOnly report setup filters to the active RX variable contract and requires every active RX variable to be present.
- TxRx report setup filters to the active TxRx variable contract and requires every active TxRx variable to be present.
- Solve-enabled setup must not release the desktop before analysis/report export completes.

## Collaborators
- [type2_step_em_input.py](type2_step_em_input.py.md)
- [type2_step_port_assignment.py](type2_step_port_assignment.py.md)
- [type2_step_em_solve.py](type2_step_em_solve.py.md)
