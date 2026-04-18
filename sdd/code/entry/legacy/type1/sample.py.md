---
title: legacy type1 sample.py
created: 2026-04-18 @ 23:10
updated: 2026-04-18 @ 23:10
tags:
  - legacy_type1
  - sampling
---

# legacy type1 sample.py

## Source
- Path: `entry/legacy/type1/sample.py`
- Code note path: `sdd/code/entry/legacy/type1/sample.py.md`
- Related diagram: [[sdd/diagrams/sample-build-flow]]

## 역할
- frozen legacy type1 batch profile 계산, feasible seed selection, sample artifact generation, `manifest.json` 기록을 묶는다.

## 입력 / 출력
- `iter_sample_batch_profiles(...) -> tuple[SampleBatchProfile, ...]`
- `generate_sample_manifest(...) -> list[SampleManifestEntry]`
- `generate_all_sample_manifests(...) -> list[list[SampleManifestEntry]]`
- `main() -> list[list[SampleManifestEntry]]`

## Canonical state
- canonical batch identity는 `seed_start`, `seed_end`, `target_count`를 가진 `SampleBatchProfile`이다.
- output canonical path는 `run/toml/toml_<version>_<seed_start>/manifest.json` 규칙을 따른다.

## Invariants / fail-fast
- batch count, seed span, total count는 양수여야 한다.
- legacy sample entry 생성은 fallback 없이 fail-fast contract를 따른다.

## 관련 테스트
- `tests/legacy/type1/pipeline_runs/test_run_script_sample_artifacts.py`
- `tests/legacy/type1/pipeline_runs/test_manifest_determinism.py`

## 변경 시 주의점
- frozen legacy surface라서 active type2 operator flow 설명과 섞지 않는다.
