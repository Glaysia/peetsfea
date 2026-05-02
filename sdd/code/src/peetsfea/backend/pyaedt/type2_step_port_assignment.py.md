---
title: type2_step_port_assignment.py
created: 2026-04-18 @ 09:09
updated: 2026-05-03 @ 00:00
tags:
  - em
  - pyaedt
---

# type2_step_port_assignment.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_port_assignment.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_port_assignment.py.md`
- Status: active
- Primary graph owner: [type2-em-setup-boundary](../../../../../architecture/type2-em-setup-boundary.md)

## 역할
- setup-ready runtime에서 explicit lumped port를 만든다.
- `RxOnly` mode는 RX port만 생성한다.
- `TxRx` mode는 `tx_inner_single_coil`의 `tx_inner_port_sheet`를 TX 단자(`TX_TML`)로,
  RX의 `rx_port_sheet`를 RX 단자(`RX_TML`)로 assign한다.

## 입력 / 출력
- 입력: imported TX inner/RX conductor geometry, terminal metadata, HFSS modeler/boundary setup APIs
- 출력: one RX lumped port assignment for `RxOnly`; TX inner + RX lumped port assignments for `TxRx`
- 입/출력: TX inner 쌍 처리 시 역할 쌍은 정확히 `{"tx_inner_single_coil","rx_single_coil"}`.

## Canonical state
- RxOnly boundary/excitation naming is `1` / `1_T1`.
- RX port sheet is reconstructed runtime geometry, not a STEP imported body.
- TX terminal 이름은 기존 레거시/향후 보고서 문맥(`TX_TML`/`RX_TML`) 정합 기준으로 사용한다; 실제 바운더리명은 `1_T1`, `2_T1`이다.
- TxRx에서 TX 역할은 `tx_inner_single_coil`만 허용하며, 일반 `tx_single_coil` 포트는 이 루트에서 할당하지 않는다.

## Invariants / fail-fast
- Missing or ambiguous RX terminal edges fail immediately.
- PyAEDT false returns fail immediately with context.
- RxOnly must not create TX port sheets, TX lumped ports, or TX excitations.
- TxRx에서 누락되거나 잘못된 `terminal_metadata`는 즉시 에러.
- 잘못된 역할/미지원 역할 조합은 즉시 ValueError.
- 포트 시트/도체 이름은 `imported_object_names`에서 정확 일치하지 않으면 즉시 실패.

## Graph links
- Primary owner: [type2-em-setup-boundary](../../../../../architecture/type2-em-setup-boundary.md)
- Direct handoff: [type2_step_em_input.py](type2_step_em_input.py.md)
- Direct handoff: [type2_step_setup_ready.py](type2_step_setup_ready.py.md)
- Exceptional contract: [type2-em-report-contract](../../../../../architecture/type2-em-report-contract.md)
