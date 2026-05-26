---
title: test_setup_type2_step_entry.py
created: 2026-04-17 @ 09:09
updated: 2026-05-13 @ 00:00
tags:
  - hfss-import
  - em
---

# test_setup_type2_step_entry.py

## Source
- Path: `tests/type2/test_setup_type2_step_entry.py`
- Code note path: `sdd/code/tests/type2/test_setup_type2_step_entry.py.md`
- Tested source: [setup_type2_step.py](../../entry/setup_type2_step.py.md)

## 역할
- active type2 examples가 0.2.24 TxRx setup-ready contract를 표현하는지 검증한다.
- Generic TX modeled role, TX sampled-owner block이 active example surface로 돌아오면 실패한다.
- `tx_inner_single_coil` is the active TxRx TX geometry and must expose the fixed actual-region underlay stack contract.

## 입력 / 출력
- 입력:
  - `examples/type2_fixed.toml`
  - `examples/type2_sweep.toml`
  - test-local mutated TOML payloads for rejection coverage
- 출력:
  - parsed TOML assertions
  - expected rejection assertions

## Canonical state
- active example TOML payload가 canonical assertion surface다.
- active examples fix `tx_reference_line.x_ratio = 0.99` while preserving fixed/sampled `y_usage_ratio` for
  retained non-modeled `tx_inner_region` guide export.
- active sweep fixes `tx_reference_line.y_usage_ratio` and `tx_reference_line.z_ratio` to the same singleton guide values used by the fixed example.
- active examples set fixed non-modeled `tx_region` bounds to `size_x=720.0`, `origin_y=-600.0`, and `size_y=1200.0`.
- active examples preserve TX inner `y_ratio` as the actual-coil Y sizing ratio.
- active single-coil examples use quarter-turn field names `x_ratio`, `y_ratio`, `turn_qcount`, `void_factor`, `terminal_start`, and `void_stack_present`; legacy `outer_x_usage_ratio`, `outer_y_usage_ratio`, `turn_count`, `void_usage_ratio`, and `terminal_path` must stay absent.
- active example outputs use `TxRx` mode and the shared active TxRx output variable registry.
- active example `tx_inner_single_coil` uses fixed `underlay_repeat_count = [true, 1, 1, 1]`,
  `underlay_pet_psa_thickness_mm = [false, 6.0, 6.0, 1]`, and
  `underlay_ferrite_thickness_mm = [false, 6.0, 6.0, 1]`.
- active sweep examples assert TX inner and RX `turn_qcount` ranges as `[true, 4, 12, 9]`; fixed examples remain unchanged at `[true, 4, 4, 1]`.
- active examples fix `tx_inner_rect_void_coil.layer_count = [true, 1, 1, 1]` and must not expect
  `tx_inner_copper_stack` in fixed/sweep body-name contracts.
- active examples define `tv_aluminum_plate` as optional finite-conductivity sheet metadata sourced from the `tv` `+X` face, not as a STEP solid.
- active sweep exposes `non_model_objects.tx_region.z_gap_from_rx_plane_mm = [false, 45.0, 130.0, 17]` while fixing `modeled_objects.tv_aluminum_plate.sheet_present = [true, 0, 0, 1]`, setting the active sampled-owner count to 15.
- active sweep exposes `terminal_start = [true, 0, 3, 4]` and `void_stack_present = [true, 0, 1, 2]` for both TX inner and RX single-coil objects.
- active fixed exposes `modeled_objects.tv_aluminum_plate.sheet_present = [true, 0, 0, 1]`, preserving a sheet-absent fixed realization.

## Invariants / fail-fast
- `outputs.mode` must be `TxRx`.
- active outputs must match the TxRx report variable list in [type2-em-report-contract](../../../architecture/type2-em-report-contract.md).
- active modeled objects must contain `tx_inner_single_coil` plus RX modeled object(s), and no generic
  TX modeled role.
- active examples must expose `tx_region.z_gap_from_rx_plane_mm` as the canonical TX guide Z-gap owner but must not expose TX derived sampled owners such as `tx_region_actual`, `tx_region_actual_stack_space`, or TX modeled sampled fields.
- fixed example `turn_qcount` ranges must stay singleton one-turn ranges while the official sweep upper bound stays at three turns represented as quarter-turn count `12`.
- active examples must not expose `modeled_objects.tx_inner_rect_void_coil.layer_count` as a sampled owner.
- active examples must not declare `tv_aluminum_plate.primitive = "box"` or any other STEP-solid primitive.
- active sweep sampled-owner paths must include `non_model_objects.tx_region.z_gap_from_rx_plane_mm`, both `terminal_start` owners, and both `void_stack_present` owners, exclude fixed TV sheet presence and reference-line ratios, and have length 15.
- `tx_reference_line.x_ratio`, `tx_reference_line.y_usage_ratio`, and `tx_reference_line.z_ratio` are guide-only
  inputs and may derive TX inner geometry context, but must not imply TX ports, reports, generic TX modeled roles,
  or active TX derived sampled owners.
  `tx_region.z_gap_from_rx_plane_mm` is allowed because it controls non-modeled guide Z placement.

## 직접 의존
- [type2-em-report-contract](../../../architecture/type2-em-report-contract.md)
- [0.2.24-type2-rxonly-tx-removal](../../../plans/0.2.24-type2-rxonly-tx-removal.md)
- [0.2.24-type2-tx-inner-region-non-model-step](../../../plans/0.2.24-type2-tx-inner-region-non-model-step.md)
- [0.2.24 Type2 TX Inner Actual Underlay Stack](../../../plans/0.2.24-type2-tx-inner-actual-underlay-stack.md)
- [0.2.24-type2-tx-region-y-1800-x-reference-fixed](../../../plans/0.2.24-type2-tx-region-y-1800-x-reference-fixed.md)
- [0.2.24-type2-turn-count-sweep-upper-bound](../../../plans/0.2.24-type2-turn-count-sweep-upper-bound.md)
- [0.2.25-type2-tv-aluminum-sheet-presence](../../../plans/0.2.25-type2-tv-aluminum-sheet-presence.md)
- [0.2.25-type2-quarter-turn-single-coil](../../../plans/0.2.25-type2-quarter-turn-single-coil.md)

## 이 파일을 쓰는 곳
- Default pure-Python test suite.

## 관련 테스트
- This file is high-level active example coverage for RxOnly setup-ready input expectations.

## 변경 시 주의점
- real STEP export or AEDT launch를 넣지 않는다.
- parser/export/backend implementation assertions owned by other workers must stay in their own files.
