---
title: type2_sampled.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
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
- sampled owner canonical paths are `modeled_objects.<object_id>.<field>` and `non_model_objects.<object_id>.<field>`.
- `tx_region` may be present as a fixed guide; it is not a sampled TX geometry owner in the reset contract.
- constraints are preserved in sampled TOML and evaluated as deterministic sampling feasibility filters.
- `retry_number` records the first constraint-satisfying retry attempt and remains part of the `design_id`.
- manifest `entries` contains only successful sampled designs; validation/infeasible attempts are recorded in top-level `skipped`.
- stage reporting is runtime visibility only and is not canonical sampled state.

## Invariants / fail-fast
- sampled metadata owner list must exactly match the source exportable sampled owner set.
- usage-ratio design variables are unitless; only `_mm` owners receive `mm` expressions.
- RxOnly sampling must not require TX modeled owners.
- type2 constraints must be evaluated before sampled TOML is written.
- constraint retry budget is fixed; exhausted candidates are recorded as skipped only for expected validation/infeasible failures.
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
