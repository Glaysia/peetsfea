---
title: test_sample_type2_entry.py
created: 2026-04-18 @ 09:09
updated: 2026-05-27 @ 00:00
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
- 0.2.25 quarter-turn RxOnly owner discovery, guide/context handling, and fixed-zero X-position compatibility handling are active.

## Canonical state
- Sampling remains deterministic by source TOML, version, seed, and retry number.
- RX single-coil sampled fixtures preserve the active `3.965 mm` PCB plus `0.035 mm` copper stack.
- Active single-coil sampled fixture names are `x_ratio`, `y_ratio`, `turn_qcount`, `void_factor`, `metal_fill_factor`, `terminal_start`, and `void_stack_present`.
- `tx_region` is guide context only; singleton `z_gap_from_rx_plane_mm` and singleton `tx_reference_line.x_ratio` are not exported sampled owners.
- `tx_region.z_gap_from_rx_plane_mm` is an effective sampled owner when its range has `count > 1`.
- Official active fixtures sample `tx_reference_line.y_usage_ratio` and `tx_reference_line.z_ratio`, so they remain active sampled metadata alongside the TX Z-gap owner.
- RxOnly sampled-owner fixtures contain TX inner and RX coil owners plus active count>1 non-modeled guide owners, including the TX Z-gap owner when sampled; TX derived non-model owners are absent.
- Synthetic `ModeledTxInnerSingleCoilSpec` fixtures include active fixed TX inner `layer_count=1` plus passive underlay defaults: repeat count `1`, PET/PSA `6.0 mm`, and ferrite `6.0 mm`.
- Synthetic sampled single-coil `turn_qcount` ranges use quarter-turn active bounds such as `[true, 3, 7, 5]` / `RangeSpec(3.0, 7.0, count=5)`.
- Non-`turn_qcount` owners such as generic TX column `layer_count` remain unchanged; fixed singleton `turn_qcount` ranges remain unchanged.
- RX sampled `turn_qcount` manifest values are members of `{3, 4, 5, 6, 7}`.
- Embedded TOML fixtures keep `modeled_objects.tx_inner_rect_void_coil.x_position_ratio` as a fixed zero compatibility field for lower-X wall-side anchoring.
- Synthetic source TOML fixtures include sampled `modeled_objects.tx_inner_rect_void_coil.void_stack_present` and `modeled_objects.rx_rect_void_coil.void_stack_present` so manifest metadata exercises both active void-stack owners.
- Synthetic source TOML fixtures fix `modeled_objects.tv_aluminum_plate.sheet_present` disabled when manifest metadata is expected to exclude the TV aluminum sheet presence owner, but the official sweep example now samples that owner.
- `seed_first` is the absolute sample index floor; emitted sample metadata and `design_id` prefixes match absolute indices (for example `seed_first=12000` produces `s012000_*`).
- Active fixed/sweep source fixtures use `modeled_objects.tx_inner_rect_void_coil.layer_count = [true, 1, 1, 1]`.
- `modeled_objects.tx_outer_rect_void_coil.*` paths are not active sampled owners.
- Active sampled TOML must not preserve `terminal_path`, removed `tx_outer_terminal_path`, or removed `tx_outer_x_position_ratio` fields.

## Invariants / fail-fast
- Unknown owner paths fail immediately.
- `sampled_owner_paths` must include every active `count > 1` range owner, including the non-modeled TX Z gap, both sampled `tx_reference_line` ratios, TV sheet presence, both `terminal_start` owners, and both `void_stack_present` owners.
- Fixtures that freeze TV aluminum `sheet_present` must keep it out of sampled owner paths, and official sampled TOML must preserve the active integer range when that owner is intentionally sampled.
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
- `manifest_entry_for_sample_index()` resolves by concrete `sample_index` values, including when `seed_first>0`; index `0` must be treated as out-of-range unless produced by the manifest.
- Lightweight spec tools must import without CAD/AEDT modules.

## Collaborators
- [sample.py](../../entry/sample.py.md)
- [type2_sampled.py](../../src/peetsfea/type2_sampled.py.md)
- [0.2.24 Type2 TX Outer Void Stack](../../../plans/0.2.24-type2-tx-outer-void-stack.md)
- [0.2.24 Type2 STEP Export Scene Data Reuse](../../../plans/0.2.24-type2-step-export-scene-data-reuse.md)
- [0.2.24-type2-tx-region-y-1800-x-reference-fixed](../../../plans/0.2.24-type2-tx-region-y-1800-x-reference-fixed.md)
- [0.2.24 Type2 Turn Count Sweep Upper Bound](../../../plans/0.2.24-type2-turn-count-sweep-upper-bound.md)
- [0.2.25 Type2 TV Aluminum Sheet Presence](../../../plans/0.2.25-type2-tv-aluminum-sheet-presence.md)
- [0.2.25 Type2 TX Region Z Gap Owner](../../../plans/0.2.25-type2-tx-region-z-gap-owner.md)
