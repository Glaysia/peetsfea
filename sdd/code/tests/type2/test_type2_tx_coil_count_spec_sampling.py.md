---
title: test_type2_tx_coil_count_spec_sampling.py
created: 2026-04-20 @ 04:35
updated: 2026-04-20 @ 13:08
tags:
  - tests
  - sampling
  - type2
---

# test_type2_tx_coil_count_spec_sampling.py

## Source
- Path: `tests/type2/test_type2_tx_coil_count_spec_sampling.py`
- Code note path: `sdd/code/tests/type2/test_type2_tx_coil_count_spec_sampling.py.md`
- Status: planned
- Related plan: [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]], [[sdd/plans/0.2.22-type2-tx-actual-region-non-model-sampling]]

## 역할
- `tx_coil_count` and `tx_array_x_usage_ratio` parser, sampling, sampled TOML freeze, and design variable contracts를 방어한다.

## 입력 / 출력
- 입력: temporary type2 TOML text and active examples
- 출력: pytest assertions for accepted/rejected specs, sampled metadata, frozen ranges, prepared design variables

## Canonical state
- `modeled_objects.tx_plate_stack.tx_coil_count` is the only sampled owner path for TX plate-stack count.
- `modeled_objects.tx_plate_stack.tx_array_x_usage_ratio` is the only sampled owner path for TX plate-stack array X span usage.
- Canonical sampled range is `[true, 1, 4, 4]`; fixed replay values are `[true, n, n, 1]`.
- Canonical X-usage sampled range is `[false, 0.1, 0.6, 14]`; fixed replay values are `[false, r, r, 1]`, `0 < r <= 1`.

## Invariants / fail-fast
- RX plate-stack must reject `tx_coil_count` and `tx_array_x_usage_ratio`.
- Noncanonical integer ranges and values outside `1..4` fail before generation.
- Sampled metadata and replay exact-match guards must include the new owner when count is sampled.
- Fixture TOML uses active type2 schema v5 and includes fixed `tx_region_actual` non-model owners so this test can focus on TX plate-stack sampled owners.

## 직접 의존
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_sampled.py]]

## 관련 테스트
- This file is the direct regression owner.

## 변경 시 주의점
- Do not couple these tests to rect/void single-coil helpers.
- Keep examples and expected sampled owner order aligned.
