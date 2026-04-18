---
title: sample.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 23:10
tags:
  - sampling
  - step
---

# entry/sample.py

- Source path: `entry/sample.py`
- Code note path: `sdd/code/entry/sample.py.md`
- Related plan: [[sdd/plans/0.2.23-type2-sampled-build-split]]
- Collaborators:
  - [[sdd/code/src/peetsfea/type2_runtime.py]]
  - [[sdd/code/src/peetsfea/type2_sampled.py]]
  - [[sdd/code/entry/generate_type2_step.py]]

## 역할
- active type2 sample + STEP owner entrypoint다.
- source TOML에서 frozen sampled TOML을 만들고 `manifest.json`을 기록한다.
- manifest 전체 entries에 대해 scene STEP과 STEP ledger를 생성한다.

## 입력 / 출력
- 입력:
  - `examples/type2_sweep.toml`
- 출력:
  - `run/sampled/type2/manifest.json`
  - `run/sampled/type2/<design_id>/sampled.toml`
  - `run/sampled/type2/<design_id>/type2_scene.step`
  - `run/sampled/type2/<design_id>/type2_step_ledger.json`

## Canonical state
- module constants가 기본 sample/runtime contract를 이룬다.
- canonical sampled design set은 `range(SEED_FIRST, SEED_FIRST + SEED_N)`다.
- manifest top-level `config`는 downstream build runtime contract를 보존한다.

## Invariants / fail-fast
- `SEED_N`, `SAMPLER_N`, `STEP_BUILDER_N`, `AEDT_BUILDER_N`는 모두 양수여야 한다.
- sampled TOML generation과 STEP export는 모두 deterministic해야 한다.
- manifest write 뒤 STEP export를 시작하며, `.aedt`는 만들지 않는다.
- manifest object shape는 list fallback 없이 고정한다.

## 직접 의존
- `peetsfea.type2_runtime`
- `peetsfea.type2_sampled`
- `entry.generate_type2_step`

## 이 파일을 직접 쓰는 곳
- `entry/build.py`
- human/agent active sample entrypoint

## 관련 테스트
- [[sdd/code/tests/type2/test_sample_type2_entry.py]]

## 변경 시 주의점
- manifest config ownership을 `entry/build.py`로 이동시키지 않는다.
- sample stage에 AEDT build를 다시 섞지 않는다.
- design directory layout을 바꾸면 build replay와 docs를 함께 갱신한다.
