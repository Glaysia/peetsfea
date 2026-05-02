---
title: Type2 EM Report Contract
created: 2026-04-28 @ 00:00
updated: 2026-05-03 @ 00:00
tags:
  - em
  - sdd
---

# Type2 EM Report Contract

이 문서는 type2 setup-ready EM 출력 변수의 shape-independent 계약이다.
현재 active runtime은 `RxOnly`와 `TxRx` 두 모드를 지원한다. `TxRx`의 활성 TX 형상은 `tx_inner_single_coil` 하나로 제한한다.

## Graph Position
- Parser enforcement owner: [type2-spec-boundary](type2-spec-boundary.md)
- Setup/report runtime owner: [type2-em-setup-boundary](type2-em-setup-boundary.md)
- Pipeline context owner: [type2-step-to-em-validate-pipeline](type2-step-to-em-validate-pipeline.md)

## Active Modes
- `RxOnly` assigns only `RX_TML`, reports RX self terms, and rejects TX or transfer expressions.
- `TxRx` assigns `TX_TML` and `RX_TML`, reports TX self, RX self, transfer, coupling, and efficiency variables, and requires both port sheets to exist.
- Generic TX modeled roles remain unsupported for EM setup unless a later plan gives them explicit import, port, mesh, and output contracts.

## Active RxOnly Variables
- `Lrx_uH`
- `Qrx_ratio`
- `Rrx_ac_ohm`
- `Xrx_ohm`
- `Grx_S`
- `Brx_S`
- `Srx_self_mag_ratio`
- `eta_rx_accept_ratio`

## Active TxRx Variables
아래 변수들은 `TxRx` 모드에서 active report 이름이다. `RxOnly`에서는 계속 금지된다.

- `Ltx_uH`
- `Lrx_uH`
- `M_uH`
- `k_ratio`
- `Qtx_ratio`
- `Qrx_ratio`
- `FOM_ratio`
- `Rtx_ac_ohm`
- `Rrx_ac_ohm`
- `Xtx_ohm`
- `Xrx_ohm`
- `M_over_Ltx_ratio`
- `M_over_Lrx_ratio`
- `Gtx_S`
- `Btx_S`
- `Grx_S`
- `Brx_S`
- `S11_mag_ratio`
- `S21_mag_ratio`
- `S21_phase_deg`
- `S22_mag_ratio`
- `eta_s21_power_ratio`
- `eta_tx_accept_ratio`
- `eta_rx_accept_ratio`
- `eta_match_product_ratio`
- `eta_s21_from_tx_accept_ratio`
- `eta_s21_from_rx_accept_ratio`
- `eta_s21_two_sided_norm_ratio`
- `eta_fom_max_ratio`

## Port Naming
- RxOnly setup creates only the RX lumped port and RX output variables.
- RxOnly must not create TX ports or TX output variables.
- TxRx setup creates the TX inner lumped port and RX lumped port from STEP ledger `terminal_metadata`.
- TX inner port sheet object name: `tx_inner_port_sheet`.
- RX port sheet object name: `rx_port_sheet`.
- TX terminal name: `TX_TML`.
- RX terminal name: `RX_TML`.
- Numeric AEDT port names remain a runtime convention, not a geometry-shape contract.

## Invariants
- Report expressions must be derived from solved terminal quantities, not from object names that encode a particular conductor shape.
- Missing terminal data is a hard failure for the mode that requires it.
- `TxRx` two-terminal variables are active validation targets only in `TxRx`.
- Generic TX roles are not implied by the `TxRx` mode; only `tx_inner_single_coil` is active in this plan.

## Related
- Direct diagram: [type2-step-to-em-validate-flow](../diagrams/type2-step-to-em-validate-flow.md)
- Direct plan: [0.2.24-type2-txrx-tx-inner-em](../plans/0.2.24-type2-txrx-tx-inner-em.md)
