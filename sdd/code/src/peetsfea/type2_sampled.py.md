---
title: type2_sampled.py
created: 2026-04-18 @ 09:09
updated: 2026-05-03 @ 00:00
tags:
  - sampling
  - build
---

# type2_sampled.py

## Source
- Path: `src/peetsfea/type2_sampled.py`
- Code note path: `sdd/code/src/peetsfea/type2_sampled.py.md`
- Status: active

## 역할
- 공개 sampling/build-prep orchestration 경계다.
- source type2 TOML에서 deterministic sampled TOML, manifest entry, skipped entry, build metadata를 만든다.
- 0.2.24 SDD 기준 active sampled owner는 RX path와 shared execution metadata 중심이다.

## 입력 / 출력
- 입력: source type2 TOML, seed range, manifest/sampled path
- 출력: sampled TOML, manifest entries, skipped attempts, prepared build metadata

## Canonical state
- sampled owner canonical paths are rooted at `modeled_objects.<object_id>` or `non_model_objects.<object_id>` and may address nested TOML tables.
- `tx_region` remains guide context; its `tx_reference_line` nested range fields are sampled non-modeled owner coordinates, not TX modeled geometry.
- `modeled_objects.tx_outer_rect_void_coil.x_position_ratio` is an exportable sampled owner even though its source TOML range is selected by `modeled_objects.tx_inner_rect_void_coil.tx_outer_x_position_ratio`; freeze logic must write the selected value back to that source selector.
- constraints are preserved in sampled TOML and evaluated as deterministic sampling feasibility filters.
- `retry_number` records the first constraint-satisfying retry attempt and remains part of the `design_id`.
- manifest `entries` contains only successful sampled designs; validation/infeasible attempts are recorded in top-level `skipped`.
- stage reporting is runtime visibility only and is not canonical sampled state.
- Omitting the exporter uses the process-safe built-in STEP exporter and may use the worker pool; explicit custom exporters stay in-process so tests and injected callbacks remain deterministic.

## Invariants / fail-fast
- sampled metadata owner list must exactly match the source exportable sampled owner set.
- sampled TOML freeze logic must support every sampled owner path shape emitted by owner discovery, including nested non-modeled paths.
- sampled TOML freeze logic must preserve the derived outer companion source structure and must not require an explicit `tx_outer_rect_void_coil` TOML table.
- usage-ratio design variables are unitless; only `_mm` owners receive `mm` expressions.
- RxOnly sampling must not require TX modeled owners.
- type2 constraints must be evaluated before sampled TOML is written.
- constraint retry budget is fixed; exhausted candidates are recorded as skipped only for expected validation/infeasible failures.
- STEP/CAD export dependencies are imported only by orchestration paths that actually build STEP artifacts.
- `make_step_on_sample=True` with the built-in exporter must not be forced into the serial custom-exporter path.
- non-validation exceptions remain fail-fast.

## Collaborators
- [type2_step_spec.py](type2_step_spec.py.md)
- [type2_runtime.py](type2_runtime.py.md)
- [build.py](../../entry/build.py.md)
- [type2_step_export.py](type2_step_export.py.md)
- [type2_sampled_skip.py](type2_sampled_skip.py.md)

## 관련 테스트
- [test_sample_type2_entry.py](../../tests/type2/test_sample_type2_entry.py.md)
- [test_build_type2_entry.py](../../tests/type2/test_build_type2_entry.py.md)

## 변경 시 주의점
- TX shape sampled owners must not be reintroduced while the 0.2.24 reset is active.
- Replay metadata exact-match guards must stay synchronized with active RX owner paths.
