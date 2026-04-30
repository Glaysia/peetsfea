---
title: test_setup_type2_step_entry.py
created: 2026-04-17 @ 09:09
updated: 2026-04-28 @ 23:59
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
- `tx_inner_single_coil` is the active TxRx TX geometry and must keep fixed zero underlay.

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
- active examples include fixed/sampled `tx_reference_line` ratio inputs, including `y_usage_ratio`, for
  retained non-modeled `tx_inner_region` guide export.
- active example outputs use `TxRx` mode and the shared active TxRx output variable registry.

## Invariants / fail-fast
- `outputs.mode` must be `TxRx`.
- active outputs must match the TxRx report variable list in [type2-em-report-contract](../../../architecture/type2-em-report-contract.md).
- active modeled objects must contain `tx_inner_single_coil` plus RX modeled object(s), and no generic
  TX modeled role.
- active examples must not expose TX derived sampled owners such as `tx_region_actual`, `tx_region_actual_stack_space`, or TX modeled sampled fields.
- `tx_reference_line.x_ratio`, `tx_reference_line.y_usage_ratio`, and `tx_reference_line.z_ratio` are guide-only
  inputs and may derive TX inner geometry context, but must not imply TX ports, reports, generic TX modeled roles,
  or active TX sampled owners.

## 직접 의존
- [type2-em-report-contract](../../../architecture/type2-em-report-contract.md)
- [0.2.24-type2-rxonly-tx-removal](../../../plans/0.2.24-type2-rxonly-tx-removal.md)
- [0.2.24-type2-tx-inner-region-non-model-step](../../../plans/0.2.24-type2-tx-inner-region-non-model-step.md)

## 이 파일을 쓰는 곳
- Default pure-Python test suite.

## 관련 테스트
- This file is high-level active example coverage for RxOnly setup-ready input expectations.

## 변경 시 주의점
- real STEP export or AEDT launch를 넣지 않는다.
- parser/export/backend implementation assertions owned by other workers must stay in their own files.
