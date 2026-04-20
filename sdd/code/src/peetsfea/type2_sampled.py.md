---
title: type2_sampled.py
created: 2026-04-18 @ 09:09
updated: 2026-04-20 @ 14:08
tags:
  - sampling
  - build
---

# type2_sampled.py

## Source
- Path: `src/peetsfea/type2_sampled.py`
- Code note path: `sdd/code/src/peetsfea/type2_sampled.py.md`
- Status: active
- Related feature plans: [[sdd/plans/0.2.22-type2-sampled-build-split]], [[sdd/plans/0.2.22-type2-rx-plate-stack-striped-copper]], [[sdd/plans/0.2.22-type2-plate-stack-z-usage-ratio]], [[sdd/plans/0.2.22-type2-plate-stack-y-usage-ratio]], [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]], [[sdd/plans/0.2.22-type2-single-coil-void-usage-ratio]], [[sdd/plans/0.2.22-type2-tx-actual-region-non-model-sampling]]

## 역할
- type2 sampled owner-path selection, frozen sampled TOML rendering, manifest/build planning을 담당한다.
- in-process STEP export path에서 entrypoint가 coarse stage 로그를 받을 수 있도록 optional reporter callback을 중계한다.

## 입력 / 출력
- 입력: source type2 TOML, seed range, manifest/sampled path
- 출력: sampled TOML, manifest entries, prepared build metadata

## Canonical state
- sampled owner canonical paths are `modeled_objects.<object_id>.<field>` and `non_model_objects.<object_id>.<field>`.
- active TX actual-region non-model sampled owners are `non_model_objects.tx_region_actual.x_usage_ratio`, `y_usage_ratio`, `x_division_count`, and `y_division_count`.
- active RX single-coil sampled outer envelope owners use `outer_x_usage_ratio` and `outer_y_usage_ratio`.
- active single-coil sampled void owner is `void_usage_ratio`; it is unitless and freezes into sampled TOML like other range owners.
- removed legacy split/centered single-coil `void_*` fields are not sampled owners and must not appear in sampled metadata or build design variables.
- active `tx_plate_stack`와 `rx_plate_stack`도 sampled owner를 가질 수 있다.
- active sweep contract에서 plate-stack sampled owners는 source order 기준으로
  - `modeled_objects.tx_plate_stack.turn_count`
  - `modeled_objects.tx_plate_stack.metal_fill_factor`
  - `modeled_objects.tx_plate_stack.z_usage_ratio`
  - `modeled_objects.tx_plate_stack.y_usage_ratio`
  - `modeled_objects.tx_plate_stack.tx_coil_count`
  - `modeled_objects.tx_plate_stack.tx_array_x_usage_ratio`
  - `modeled_objects.rx_plate_stack.turn_count`
  - `modeled_objects.rx_plate_stack.metal_fill_factor`
  - `modeled_objects.rx_plate_stack.z_usage_ratio`
  - `modeled_objects.rx_plate_stack.y_usage_ratio`
  이다.
- build path planning은 여전히 `run/sampled/type2/<design_id>/` layout을 쓴다.
- STEP stage reporter는 manifest entry나 sampled TOML에 기록되는 canonical state가 아니라 runtime notification surface다.

## Invariants / fail-fast
- sampled metadata owner list는 source exportable sampled owner set과 exact match여야 한다.
- usage-ratio design variables, including `void_usage_ratio`, are unitless; only `_mm` owners receive `mm` expressions.
- plate roles에서 terminal-path driven coil-only sampled field assert를 요구하면 안 된다.
- plate-stack free range owners는 deterministic seed selection으로 scalar로 freeze되고 sampled metadata에 그대로 기록되어야 한다.
- `tx_coil_count` is an integer owner and design variable expression is unitless.
- `tx_array_x_usage_ratio` is a floating owner and design variable expression is unitless.
- non-model usage-ratio design variables are unitless and must freeze into sampled TOML with count `1`, same as modeled usage ratios.
- non-model division-count design variables are integer/unitless and must freeze into sampled TOML with count `1`.
- This file exceeds 800 lines; this narrow extension is allowed, but future sampler restructuring should split ownership first.
- stage reporting이 실패/지원 여부를 바꾸면 안 되며, exporter failure는 기존처럼 즉시 raise되어야 한다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_runtime.py]]
- [[sdd/code/entry/build.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_sample_type2_entry.py]]
- [[sdd/code/tests/type2/test_build_type2_entry.py]]

## 변경 시 주의점
- sampled path ownership을 role-blind single-coil field enumeration으로 되돌리지 않는다.
- active example role 교체와 sampled owner list expectations를 같이 갱신해야 한다.
- plate-stack sampled owner surface adds TX-only `tx_coil_count` and `tx_array_x_usage_ratio`; replay metadata exact-match guard must stay synchronized with this owner set.
- multi-worker sample path는 completion progress ordering을 깨지 않도록 별도 process-event channel 없이 기존 completion-only progress를 유지한다.
