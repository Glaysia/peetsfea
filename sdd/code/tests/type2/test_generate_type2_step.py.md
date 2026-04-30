---
title: test_generate_type2_step.py
created: 2026-04-18 @ 09:09
updated: 2026-04-30 @ 23:59
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
- Tests cover the `tx_outer_region` non-modeled guide prism derived from semantic `tx_region` and `tx_inner_region` edges.
- Tests cover derived `tx_outer_single_coil` modeled geometry emitted from the inner TX spec and fixed `A_cw_to_a` outer terminal selector.
- Tests cover `tx_inner_actual_region` as a non-modeled coil-fit envelope derived before modeled coil construction.

## Canonical state
- RX exported body names/counts and terminal metadata remain deterministic.
- RX single-coil example geometry uses `pcb_thickness_mm = 3.965` and `copper_thickness_mm = 0.035`.
- RX full-backing thickness assertions derive the active coil stack thickness from exported PCB/copper bounds.
- TX inner active example geometry uses `pcb_thickness_mm = 0.3` and one-ounce `copper_thickness_mm = 0.035`.
- TX inner terminal metadata remains deterministic and can drive `tx_inner_port_sheet` for `TxRx`.
- `tx_inner_rect_void_coil` is modeled geometry-only with expected bodies `tx_inner_pcb_l0`,
  `tx_inner_pcb_l1`, and `tx_inner_copper_stack`; it must not create `TX_TML`.
- Multilayer TX inner tests must include the active sweep upper bound: fixed `layer_count=8` exports
  `tx_inner_pcb_l0` through `tx_inner_pcb_l7` plus `tx_inner_copper_stack`.
- `tx_inner_rect_void_coil` must be centered inside the resolved `tx_inner_region` owner in X and Y.
- `tx_outer_rect_void_coil` must be a modeled companion with role `tx_outer_single_coil`, placement owner `tx_outer_region`, and no independent sampled owner paths.
- `tx_region` may be present as guide context only.
- Deterministic tx_inner body-name contract is now explicitly covered for a fixed `layer_count=8` realization:
  expected exported bodies are `tx_inner_pcb_l0` through `tx_inner_pcb_l7` plus `tx_inner_copper_stack`.
- `tx_reference_line` ratio inputs, including centered `y_usage_ratio`, are expected to derive a visible non-modeled
  `tx_inner_region` STEP and retained ledger member without activating TX
  modeled geometry.
- `tx_outer_region` must follow source-region semantic `+X/+Z` edges and resolved TX inner stack height, without fixed example-coordinate coupling or clipping to `tx_region`.
- `tx_inner_actual_region` must match the resolved TX inner design outer box for the same TOML and seed while leaving `tx_inner_region` as the larger guide region. The modeled material/body bbox must be contained in X/Y, not equal.

## Invariants / fail-fast
- Exported body drift and generic names fail.
- RxOnly EM export tests may include TX inner modeled bodies, but must not require TX terminal EM setup,
  TX outputs, or `TX_TML`.
- Generic TX modeled roles (`tx_single_coil`, `tx_rect_void_columns`, `tx_plate_stack`) remain inactive in
  active RxOnly parser/export tests; older detailed generic-TX contracts are xfailed until that mode is
  explicitly reactivated.
- TX reference-line X/Z ratios must be strictly inside `(0, 1)`, Y usage ratio must be in `(0, 1]`, and invalid ratios
  must fail before STEP construction.
- TX outer guide assertions must compare against source-region ledger coordinates and provenance vertices, not sorted STEP vertices.
- TX actual-region assertions must compare against shared sizing/placement math, not post-hoc imported geometry inference.

## Collaborators
- [generate_type2_step.py](../../entry/generate_type2_step.py.md)
- [0.2.24 Type2 TX Actual Regions](../../../plans/0.2.24-type2-tx-actual-regions.md)
- [type2_step_export.py](../../src/peetsfea/type2_step_export.py.md)
- [0.2.24-type2-tx-inner-region-non-model-step](../../../plans/0.2.24-type2-tx-inner-region-non-model-step.md)
