---
title: Type2 EM Report Contract
created: 2026-04-28 @ 00:00
updated: 2026-04-28 @ 00:00
tags:
  - em
  - sdd
---

# Type2 EM Report Contract

이 문서는 type2 setup-ready EM 출력 변수의 shape-independent 계약이다.
현재 active runtime은 RxOnly 기준이며, TX 형상이 재설계되는 동안 TX geometry 자체는 SDD 계약에서 제거한다.

## Active RxOnly Variables
- `Lrx_uH`
- `Qrx_ratio`
- `Rrx_ac_ohm`
- `Xrx_ohm`
- `Grx_S`
- `Brx_S`
- `Srx_self_mag_ratio`
- `eta_rx_accept_ratio`

## Dormant Two-terminal Variables
아래 변수들은 나중에 TX 두 단자와 RX 두 단자를 다시 연결할 때 재사용할 shape-independent report 이름이다.
현재 TX 형상 명세나 TX 포트 생성 요구사항이 아니다.

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
- Future two-terminal setup may reuse `TX_TML` and `RX_TML` symbolic terminal references, but those names do not imply any current TX shape.
- Numeric port names remain a runtime convention, not a geometry-shape contract.

## Invariants
- Report expressions must be derived from solved terminal quantities, not from object names that encode a particular conductor shape.
- Missing terminal data is a hard failure for the mode that requires it.
- Dormant two-terminal variables are documentation of future report continuity only; they are not active validation targets in RxOnly.

## Related
- [type2-step-to-em-validate-pipeline](type2-step-to-em-validate-pipeline.md)
- [type2-step-to-em-validate-flow](../diagrams/type2-step-to-em-validate-flow.md)
