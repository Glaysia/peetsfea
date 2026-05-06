---
title: test_sample_type2_entry.py
created: 2026-04-18 @ 09:09
updated: 2026-05-06 @ 00:00
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
- 0.2.24 SDD 기준 RxOnly owner discovery, guide/context handling, and TX inner X-position owner mapping are active.

## Canonical state
- Sampling remains deterministic by source TOML, version, seed, and retry number.
- RX single-coil sampled fixtures preserve the active `3.965 mm` PCB plus `0.035 mm` copper stack.
- `tx_region` is guide context only, but its `tx_reference_line` range fields are effective sampled owner coordinates.
- RxOnly sampled-owner fixtures contain RX coil owners plus active non-modeled guide owners; TX derived non-model owners are absent.
- Synthetic `ModeledTxInnerSingleCoilSpec` fixtures include the required fixed PET/PSA and ferrite underlay thickness ranges so sampled-owner tests exercise the current parser dataclass contract.
- `modeled_objects.tx_inner_rect_void_coil.x_position_ratio` is a public sampled owner sourced and frozen directly on `tx_inner_rect_void_coil`.
- `modeled_objects.tx_outer_rect_void_coil.*` paths are not active sampled owners.
- Active sampled TOML must not preserve removed `tx_outer_terminal_path` or `tx_outer_x_position_ratio` fields.

## Invariants / fail-fast
- Unknown owner paths fail immediately.
- `sampled_owner_paths` must include every active `count > 1` range owner, including non-modeled guide ranges.
- RxOnly sampling tests must not require TX modeled owners.
- RxOnly sampling tests must not require `tx_region_actual` or `tx_region_actual_stack_space`.
- Fixed TX inner underlay thickness fields are not sampled owner paths because their ranges are fixed singleton values.
- Sampled owner discovery must preserve canonical `modeled_objects.tx_inner_rect_void_coil.x_position_ratio`.
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
