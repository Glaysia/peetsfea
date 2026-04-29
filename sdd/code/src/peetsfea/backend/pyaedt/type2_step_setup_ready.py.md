---
title: type2_step_setup_ready.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 13:10
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
- 0.2.24 SDD 기준 active mode is RxOnly.

## Canonical state
- RxOnly creates RX mesh, radiation boundary, one RX port, RX sources/reports, validates, and saves.
- TX guide geometry and geometry-only `tx_inner_single_coil` imported bodies may exist as context but are not setup targets.
- The full imported ledger records all imported bodies; active setup passes an RX-only modeled-object subset into mesh, port assignment, EM input, sources, and reports.
- Report variables are owned by [type2-em-report-contract](../../../../../architecture/type2-em-report-contract.md).

## Invariants / fail-fast
- PyAEDT false returns fail immediately.
- RxOnly must not create TX ports or TX output variables.
- A loaded ledger with generic/legacy modeled TX roles is rejected before HFSS setup begins; there is no paired-mode fallback path.
- A loaded ledger with exactly one `rx_single_coil` plus geometry-only `tx_inner_single_coil` is accepted, then filtered to the single RX modeled object for setup.
- RxOnly report setup filters to the active RX variable contract and requires every active RX variable to be present.

## Collaborators
- [type2_step_em_input.py](type2_step_em_input.py.md)
- [type2_step_port_assignment.py](type2_step_port_assignment.py.md)
