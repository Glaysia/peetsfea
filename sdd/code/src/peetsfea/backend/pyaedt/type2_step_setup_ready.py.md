---
title: type2_step_setup_ready.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
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
- TX guide geometry may exist as context but is not a setup target.
- Report variables are owned by [type2-em-report-contract](../../../../../architecture/type2-em-report-contract.md).

## Invariants / fail-fast
- PyAEDT false returns fail immediately.
- RxOnly must not create TX ports or TX output variables.

## Collaborators
- [type2_step_em_input.py](type2_step_em_input.py.md)
- [type2_step_port_assignment.py](type2_step_port_assignment.py.md)
