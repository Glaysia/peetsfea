---
title: test_generate_type2_step.py
created: 2026-04-18 @ 09:09
updated: 2026-04-29 @ 00:00
tags:
  - test
  - step-export
---

# test_generate_type2_step.py

## Source
- Path: `tests/type2/test_generate_type2_step.py`
- Code note path: `sdd/code/tests/type2/test_generate_type2_step.py.md`
- Status: active

## 역할
- type2 STEP export and ledger contract를 검증한다.
- 0.2.24 SDD 기준 RX EM geometry plus geometry-only `tx_inner_single_coil` retained under `tx_inner_region`
  are active.
- 2026-04-29 TxRx plan treats `tx_inner_single_coil` as an active EM setup target when the output mode is `TxRx`.
- Tests in this file should include TxRx-facing assertions that verify generated ledgers preserve `tx_inner_single_coil` and `rx_single_coil` modeled entries for downstream setup-ready consumption.

## Canonical state
- RX exported body names/counts and terminal metadata remain deterministic.
- TX inner terminal metadata remains deterministic and can drive `tx_inner_port_sheet` for `TxRx`.
- `tx_inner_rect_void_coil` is modeled geometry-only with expected bodies `tx_inner_pcb_l0`,
  `tx_inner_pcb_l1`, and `tx_inner_copper_stack`; it must not create `TX_TML`.
- `tx_inner_rect_void_coil` must be centered inside the resolved `tx_inner_region` owner in X and Y.
- `tx_region` may be present as guide context only.
- `tx_reference_line` ratio inputs, including centered `y_usage_ratio`, are expected to derive a visible non-modeled
  `tx_inner_region` STEP and retained ledger member without activating TX
  modeled geometry.

## Invariants / fail-fast
- Exported body drift and generic names fail.
- RxOnly EM export tests may include TX inner modeled bodies, but must not require TX terminal EM setup,
  TX outputs, or `TX_TML`.
- Generic TX modeled roles (`tx_single_coil`, `tx_rect_void_columns`, `tx_plate_stack`) remain inactive in
  active RxOnly parser/export tests; older detailed generic-TX contracts are xfailed until that mode is
  explicitly reactivated.
- TX reference-line X/Z ratios must be strictly inside `(0, 1)`, Y usage ratio must be in `(0, 1]`, and invalid ratios
  must fail before STEP construction.

## Collaborators
- [generate_type2_step.py](../../entry/generate_type2_step.py.md)
- [type2_step_export.py](../../src/peetsfea/type2_step_export.py.md)
- [0.2.24-type2-tx-inner-region-non-model-step](../../../plans/0.2.24-type2-tx-inner-region-non-model-step.md)
