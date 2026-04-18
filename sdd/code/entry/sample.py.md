---
title: sample.py
created: 2026-04-17 @ 09:09
updated: 2026-04-19 @ 10:35
tags:
  - sampling
  - step
---

# entry/sample.py

- Source path: `entry/sample.py`
- Code note path: `sdd/code/entry/sample.py.md`
- Related plan: [[sdd/plans/0.2.23-type2-sampled-build-split]]
- Collaborators:
  - [[sdd/code/src/peetsfea/type2_sampled.py]]
  - [[sdd/code/src/peetsfea/type2_step_export.py]]

## 역할
- active type2 sample + STEP owner entrypoint다.
- source TOML에서 frozen sampled TOML과 scene STEP을 함께 만든다.
- sample runtime은 단계 시작/진행률/완료 요약을 stdout에 계속 기록한다.
- interactive terminal에서는 하단 status line 하나를 carriage-return으로 계속 갱신해 현재 퍼센트와 마지막 완료 항목을 보여준다.
- 모든 sampled design이 끝난 뒤 `manifest.json`을 기록한다.
- 완료 요약에는 전체 wall-clock `elapsed_s`를 포함한다.

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
- `SAMPLER_N`은 sampled TOML + STEP combined worker count다.
- progress line은 sample completion order 기준으로 매건 1회 출력한다.
- status line은 `0/total` waiting 상태로 시작해서 매 완료 직후 퍼센트/완료수/마지막 완료 idx를 덮어쓴다.
- done line은 `elapsed_s=<seconds>`를 고정 소수점 문자열로 남긴다.
- `design_id`는 seed가 아니라 `sample_index + generated_hash4 + head_hash4 + retry_number` 조합이다.

## Invariants / fail-fast
- `SEED_N`, `SAMPLER_N`, `AEDT_BUILDER_N`는 모두 양수여야 한다.
- sampled TOML generation과 STEP export는 같은 sample worker path 안에서 deterministic해야 한다.
- `.aedt`는 만들지 않는다.
- manifest object shape는 list fallback 없이 고정한다.
- notebook-visible sampled index는 `entries` 배열 순서를 그대로 쓴다.
- live status line은 stage 경계에서 newline으로 정리한 뒤 다음 info line을 써야 한다.

## 직접 의존
- `peetsfea.type2_sampled`
- `peetsfea.type2_step_export`

## 이 파일을 직접 쓰는 곳
- `entry/build.py`
- human/agent active sample entrypoint

## 관련 테스트
- [[sdd/code/tests/type2/test_sample_type2_entry.py]]

## 변경 시 주의점
- manifest config ownership을 `entry/build.py`로 이동시키지 않는다.
- sample을 다시 `sampled.toml only`와 `step build`로 분리하지 않는다.
- design directory layout을 바꾸면 build replay와 docs를 함께 갱신한다.
