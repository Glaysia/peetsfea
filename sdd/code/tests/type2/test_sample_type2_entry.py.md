---
title: test_sample_type2_entry.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 21:05
tags:
  - tests
  - type2
  - sampling
---

# test_sample_type2_entry.py

## Source
- Path: `tests/type2/test_sample_type2_entry.py`
- Code note path: `sdd/code/tests/type2/test_sample_type2_entry.py.md`
- Direct owner: [[sdd/plans/0.2.22-type2-sampled-build-split]], [[sdd/plans/0.2.22-type2-plate-stack-z-usage-ratio]], [[sdd/plans/0.2.22-type2-plate-stack-y-usage-ratio]], [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]], [[sdd/plans/0.2.22-type2-single-coil-void-usage-ratio]], [[sdd/plans/0.2.22-type2-tx-actual-region-non-model-sampling]], [[sdd/plans/0.2.22-type2-tx-actual-region-pcb-non-model]], [[sdd/plans/0.2.22-type2-tx-rect-void-columns-geometry]]
- Direct verification target: [[sdd/code/entry/sample.py]]
- Discovery bridge: [[sdd/code/tests/type2/test_build_type2_entry.py]]

## 역할
- sampled TOML, manifest metadata, sampled owner-path selection contract를 검증한다.
- sample entrypoint의 operator-facing progress/stage stdout contract를 검증한다.

## Canonical coverage
- active example uses RX single-coil source only
- active RX-only example keeps RX single-coil as the only modeled object and adds sampled non-model `tx_region_actual` X/Y usage, X/Y division owners, and `tx_region_actual_stack_space.scale_ratio`; `tx_region_actual_stack_space.tilt_enabled` remains fixed on.
- tx-rect-void-columns example verifies shared TX owner sampling is independent from RX owner-range changes.
- tx-rect-void-columns sample metadata includes only effective `turn_count_x*` owner paths for the resolved `tx_region_actual.x_division_count` and excludes inactive `turn_count_x*` paths.
- tx-rect-void-columns sample metadata excludes `outer_x_usage_ratio` and `outer_y_usage_ratio` because the TX outer footprint is owned by `tx_region_actual_stack_space`.
- tx-rect-void-columns examples keep `terminal_stub_length_mm` fixed at 10.0 mm for floorward geometry-only stubs, so it is not an effective sampled owner until intentionally reopened.
- sampled owner paths cover only `rx_rect_void_coil` effective sampled degrees:
  - `outer_x_usage_ratio`
  - `outer_y_usage_ratio`
  - `void_usage_ratio`
  - `turn_count`
  - `metal_fill_factor`
- `rx_rect_void_coil.layer_count` stays fixed `count=1` and is not part of sampled owner paths.
- `rx_rect_void_coil.underlay_repeat_count` is fixed for full backing and is not part of sampled owner paths.
- sampled TOML keeps non-sampled RX fields as fixed scalar ranges.
- sampled TOML excludes removed split/centered `void_*` fields and keeps usage ratios, including `void_usage_ratio`, unitless.
- manifest identity and hash contract remain unchanged
- sampled metadata and manifest owner paths include the four `non_model_objects.tx_region_actual.*` owners plus `non_model_objects.tx_region_actual_stack_space.scale_ratio` before modeled RX owners.
- `MAKE_STEP_ON_SAMPLE=True` path emits coarse STEP stage lines around export.
- `MAKE_STEP_ON_SAMPLE=False` does not emit STEP stage lines and does not call the exporter.

## 변경 시 주의점
- sampled owner assertions를 role-blind로 환원하지 않는다.
- non-model owner freezing must update the `[[non_model_objects]]` table, not synthesize modeled placeholders.
- stage-log assertions는 manifest JSON shape나 design identity contract를 대체하지 않는다.
