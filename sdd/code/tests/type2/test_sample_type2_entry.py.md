---
title: test_sample_type2_entry.py
created: 2026-04-18 @ 09:09
updated: 2026-05-07 @ 00:00
tags:
  - test
  - sampling
---

# test_sample_type2_entry.py

## Source
- Path: `tests/type2/test_sample_type2_entry.py`
- Code note path: `sdd/code/tests/type2/test_sample_type2_entry.py.md`
- Status: active

## 역할
- type2 sampling entrypoint and manifest behavior를 검증한다.
- `entry/sample.py --build-step` opt-in behavior and sample-only CLI default를 검증한다.
- CLI override tests verify diagnostic seed range and worker-count arguments flow into manifest config without changing defaults.
- 0.2.24 SDD 기준 RxOnly owner discovery, guide/context handling, and fixed-zero TX inner X-position compatibility handling are active.

## Canonical state
- Sampling remains deterministic by source TOML, version, seed, and retry number.
- RX single-coil sampled fixtures preserve the active `3.965 mm` PCB plus `0.035 mm` copper stack.
- `tx_region` is fixed guide context only; singleton `tx_reference_line.x_ratio` is not an exported sampled owner.
- `tx_reference_line.y_usage_ratio` remains an effective sampled owner when its range has `count > 1`.
- `tx_reference_line.z_ratio` remains an effective sampled owner with active sweep bounds `[false, 0.75, 1.0, 65]`.
- RxOnly sampled-owner fixtures contain RX coil owners plus active count>1 non-modeled guide owners; TX derived non-model owners are absent.
- Synthetic `ModeledTxInnerSingleCoilSpec` fixtures include active fixed TX inner `layer_count=1` plus passive underlay defaults: repeat count `1`, PET/PSA `6.0 mm`, and ferrite `6.0 mm`.
- Synthetic sampled single-coil `turn_count` ranges use canonical active bounds `[true, 2, 5, 4]` / `RangeSpec(2.0, 5.0, count=4)`.
- Non-`turn_count` owners such as generic TX column `layer_count` remain unchanged; fixed singleton `turn_count` ranges remain unchanged.
- RX sampled `turn_count` manifest values are members of `{2, 3, 4, 5}`.
- Embedded TOML fixtures keep `modeled_objects.tx_inner_rect_void_coil.x_position_ratio` as a fixed zero compatibility field for lower-X wall-side anchoring.
- Synthetic source TOML fixtures include sampled `modeled_objects.tx_inner_rect_void_coil.void_stack_present` so manifest metadata exercises the active TX inner void-stack owner.
- Active fixed/sweep source fixtures use `modeled_objects.tx_inner_rect_void_coil.layer_count = [true, 1, 1, 1]`.
- `modeled_objects.tx_outer_rect_void_coil.*` paths are not active sampled owners.
- Active sampled TOML must not preserve removed `tx_outer_terminal_path` or `tx_outer_x_position_ratio` fields.

## Invariants / fail-fast
- Unknown owner paths fail immediately.
- `sampled_owner_paths` must include every active `count > 1` range owner, including non-modeled Y/Z guide ranges and TX inner `void_stack_present`, and exclude fixed singleton X guide ranges.
- RxOnly sampling tests must not require TX modeled owners.
- RxOnly sampling tests must not require `tx_region_actual` or `tx_region_actual_stack_space`.
- Fixed TX inner underlay thickness fields are not sampled owner paths because their ranges are fixed singleton values.
- Fixed TX inner `layer_count=1` is not a sampled owner path.
- Sampled owner discovery must keep TX inner `x_position_ratio` as fixed zero compatibility state, not as an effective sampled owner.
- Sampled owner discovery must exclude every `modeled_objects.tx_outer_rect_void_coil.*` path.
- TX modeled-role fixtures assert parser/sampling fail-fast behavior instead of sampled manifest success.
- TX inner trace-width feasibility is validated as a sample-time constraint so retry occurs before STEP export.
- Default `--build-step`/sample API usage must preserve the parallel worker path by not passing the entrypoint exporter as a custom callback.
- CLI seed/worker overrides must be process-local manifest configuration, not module-level default mutation.
- Lightweight spec tools must import without CAD/AEDT modules.

## Collaborators
- [sample.py](../../entry/sample.py.md)
- [type2_sampled.py](../../src/peetsfea/type2_sampled.py.md)
- [0.2.24 Type2 TX Outer Void Stack](../../../plans/0.2.24-type2-tx-outer-void-stack.md)
- [0.2.24 Type2 STEP Export Scene Data Reuse](../../../plans/0.2.24-type2-step-export-scene-data-reuse.md)
- [0.2.24-type2-tx-region-y-1800-x-reference-fixed](../../../plans/0.2.24-type2-tx-region-y-1800-x-reference-fixed.md)
- [0.2.24 Type2 Turn Count Sweep Upper Bound](../../../plans/0.2.24-type2-turn-count-sweep-upper-bound.md)
