---
title: type2_sampled.py
created: 2026-04-18 @ 09:09
updated: 2026-04-21 @ 23:05
tags:
  - sampling
  - build
---

# type2_sampled.py

## Source
- Path: `src/peetsfea/type2_sampled.py`
- Code note path: `sdd/code/src/peetsfea/type2_sampled.py.md`
- Status: active
- Related feature plans: [[sdd/plans/0.2.22-type2-sampled-build-split]], [[sdd/plans/0.2.22-type2-rx-plate-stack-striped-copper]], [[sdd/plans/0.2.22-type2-plate-stack-z-usage-ratio]], [[sdd/plans/0.2.22-type2-plate-stack-y-usage-ratio]], [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]], [[sdd/plans/0.2.22-type2-single-coil-void-usage-ratio]], [[sdd/plans/0.2.22-type2-tx-actual-region-non-model-sampling]], [[sdd/plans/0.2.22-type2-tx-rect-void-columns-geometry]]

## 역할
- type2 sampled owner-path selection, frozen sampled TOML rendering, manifest/build planning을 담당한다.
- in-process STEP export path에서 entrypoint가 coarse stage 로그를 받을 수 있도록 optional reporter callback을 중계한다.

## 입력 / 출력
- 입력: source type2 TOML, seed range, manifest/sampled path
- 출력: sampled TOML, manifest entries, prepared build metadata

## Canonical state
- sampled owner canonical paths are `modeled_objects.<object_id>.<field>` and `non_model_objects.<object_id>.<field>`.
- source `[constraints]` rules are preserved in sampled TOML and evaluated as deterministic sampling feasibility filters.
- constraint retry attempts reuse the same source seed and sample index but select sampled candidates with the retry number included in the deterministic owner hash input (`retry_number=0` keeps the legacy hash input shape).
- active TX actual-region non-model sampled owners are `non_model_objects.tx_region_actual.x_usage_ratio`, `y_usage_ratio`, `x_division_count`, and `y_division_count`.
- active TX actual-region stack-space non-model sampled owner is `non_model_objects.tx_region_actual_stack_space.scale_ratio`.
- active TX actual-region stack-space tilt is fixed on and is not a sampled owner.
- active `tx_rect_void_columns` sampled-owner surface is mode-aware:
  - `modeled_objects.tx_rect_void_columns.connection_mode`
  - `modeled_objects.tx_rect_void_columns.turn_weight_a`
  - `modeled_objects.tx_rect_void_columns.turn_weight_b`
  - `modeled_objects.tx_rect_void_columns.turn_weight_c`
  - `modeled_objects.tx_rect_void_columns.series_total_turn_count` only when realized `connection_mode == 1`
  - `modeled_objects.tx_rect_void_columns.parallel_total_turn_count` only when realized `connection_mode == 0`
- active turn owner selection for both `series_total_turn_count` and `parallel_total_turn_count` is filtered by the realized TX columns coil count (`x_division_count * y_division_count`) so replay never freezes infeasible `*_total_turn_count < coil_count` candidates.
- legacy `turn_count_x*` tx-columns owners remain removed and must not reappear in sampled-owner resolution.
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
- `retry_number` is no longer metadata-only; it records the first constraint-satisfying retry attempt and remains part of the `design_id`.
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
- type2 constraints must be evaluated before sampled TOML is written, and failing candidates must retry until success or fail fast after the configured attempt budget.
- constraint retry budget is fixed at 64 attempts (`retry_number` 0..63); if all fail, manifest generation raises with seed/sample_index context.
- comparison constraints support path operands, numeric literal operands, and `sum(...)` operands that can mix owner paths and numeric literals.
- sampled metadata exact-match validation must use the source TOML and metadata seed to re-derive the sampled owner set before comparison.
- tx-columns inactive mode-dependent turn owner is not part of sampled metadata owner paths even when frozen to keep sampled TOML replay-complete.
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
- tx-columns mode-aware owner filtering (`series_total_turn_count` vs `parallel_total_turn_count`)을 role-agnostic 고정 목록으로 되돌리지 않는다.
- tx-columns series owner selection must keep the realized-grid feasibility filter; removing it can make ordinary sample+STEP runs fail for valid TOML ranges.
- active example role 교체와 sampled owner list expectations를 같이 갱신해야 한다.
- plate-stack sampled owner surface adds TX-only `tx_coil_count` and `tx_array_x_usage_ratio`; replay metadata exact-match guard must stay synchronized with this owner set.
- multi-worker sample path는 completion progress ordering을 깨지 않도록 별도 process-event channel 없이 기존 completion-only progress를 유지한다.
