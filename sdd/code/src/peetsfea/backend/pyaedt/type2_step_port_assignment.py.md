---
title: type2_step_port_assignment.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - em
  - pyaedt
---

# type2_step_port_assignment.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_port_assignment.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_port_assignment.py.md`
- Status: active

## 역할
- setup-ready runtime에서 explicit lumped port를 만든다.
- 0.2.24 SDD 기준 RxOnly mode는 RX port만 생성한다.

## 입력 / 출력
- 입력: imported RX conductor geometry, RX terminal metadata, HFSS modeler/boundary setup APIs
- 출력: one RX lumped port assignment

## Canonical state
- RxOnly boundary/excitation naming is `1` / `1_T1`.
- RX port sheet is reconstructed runtime geometry, not a STEP imported body.
- TX terminal names are dormant future two-terminal report context only; see [type2-em-report-contract](../../../../../architecture/type2-em-report-contract.md).

## Invariants / fail-fast
- Missing or ambiguous RX terminal edges fail immediately.
- PyAEDT false returns fail immediately with context.
- RxOnly must not create TX port sheets, TX lumped ports, or TX excitations.

## Collaborators
- [type2_step_em_input.py](type2_step_em_input.py.md)
- [type2_step_setup_ready.py](type2_step_setup_ready.py.md)
- [type2-em-report-contract](../../../../../architecture/type2-em-report-contract.md)
