---
title: sample.py
created: 2026-04-17 @ 09:09
updated: 2026-04-29 @ 17:05
tags:
  - sampling
  - step
---

# entry/sample.py

- Source path: `entry/sample.py`
- Code note path: `sdd/code/entry/sample.py.md`
- Related plan: [0.2.22-type2-sampled-build-split](../../plans/0.2.22-type2-sampled-build-split.md)
- Collaborators:
  - [type2_sampled.py](../src/peetsfea/type2_sampled.py.md)
  - [type2_step_export.py](../src/peetsfea/type2_step_export.py.md)

## 역할
- active type2 sample owner entrypoint다.
- CLI accepts `--build-step` to opt into sample-worker STEP artifact export.
- source TOML에서 frozen sampled TOML을 만들고, policy에 따라 같은 pass에서 scene STEP도 함께 만들 수 있다.
- sample runtime은 단계 시작/진행률/완료 요약을 stdout에 계속 기록한다.
- `MAKE_STEP_ON_SAMPLE=True`인 in-process sample path는 coarse STEP 단계 로그를 entry-level stdout으로 전달한다.
- validation/infeasible seed skip은 entry-level stdout에 별도 skip line으로 전달한다.
- interactive terminal에서는 하단 status line 하나를 carriage-return으로 계속 갱신해 현재 퍼센트와 마지막 완료 항목을 보여주며, step/log line 뒤에도 마지막 status line을 즉시 복원한다.
- interactive status line은 현재 terminal width 안에 들어가도록 bar 폭을 줄이고, 그래도 남는 초과 text는 잘라서 physical line wrap을 만들지 않는다.
- 모든 sampled design이 끝난 뒤 `manifest.json`을 기록한다.
- 완료 요약에는 전체 wall-clock `elapsed_s`를 포함한다.

## 입력 / 출력
- 입력:
  - `examples/type2_sweep.toml`
- 출력:
  - `run/sampled/type2/manifest.json`
  - `run/sampled/type2/<design_id>/sampled.toml`
  - optional `run/sampled/type2/<design_id>/type2_scene.step`
  - optional `run/sampled/type2/<design_id>/type2_step_ledger.json`

## Canonical state
- module constants가 기본 sample/runtime contract를 이룬다.
- canonical sampled design set은 `range(SEED_FIRST, SEED_FIRST + SEED_N)`다.
- default operator task samples the configured `SEED_N` designs and writes STEP artifacts when `MAKE_STEP_ON_SAMPLE=True`.
- manifest top-level `config`는 downstream build runtime contract를 보존한다.
- `SAMPLER_N`은 sampled TOML owner worker count다. `MAKE_STEP_ON_SAMPLE=True`일 때만 same-worker STEP export까지 맡는다.
- CLI/default `--build-step` uses the built-in sample exporter without passing it as a custom callback, so the type2 sampled worker pool remains active.
- `MAKE_STEP_ON_SAMPLE`이 sample-side STEP ownership toggle이다.
- `MAKE_STEP_ON_SAMPLE=False` is the default so ordinary sampling writes sampled TOML/manifest only.
- CLI `--build-step` overrides the default for one process and must be reflected in `manifest.config.make_step_on_sample`.
- progress line은 sample completion order 기준으로 매건 1회 출력한다.
- STEP stage line은 single-worker/in-process export 기준으로 start, exporter coarse phase, done 경계를 보여준다.
- status line은 `0/total` waiting 상태로 시작해서 매 완료 직후 퍼센트/완료수/마지막 완료 idx를 덮어쓴다.
- interactive status line clearing은 마지막 render 길이가 아니라 현재 terminal width 기준으로 한 physical line만 지운다.
- done line은 `elapsed_s=<seconds>`를 고정 소수점 문자열로 남긴다.
- final done line 뒤에는 active status line을 newline으로 종료해 VS Code task reuse prompt가 status line에 붙지 않게 한다.
- `design_id`는 seed가 아니라 `sample_index + generated_hash4 + head_hash4 + retry_number` 조합이다.
- done line reports successful `count`, `skipped`, and attempted seed count.
- manifest `entries` is successful design order; manifest `skipped` is failure ledger order.

## Invariants / fail-fast
- `SEED_N`, `SAMPLER_N`, `AEDT_BUILDER_N`는 모두 양수여야 한다.
- default constants should remain lightweight enough for the VS Code task to complete interactively under the active TOML surface.
- `MAKE_STEP_ON_SAMPLE=True`면 sampled TOML generation과 STEP export는 같은 sample worker path 안에서 deterministic해야 한다.
- `MAKE_STEP_ON_SAMPLE=False`면 sample 단계는 STEP export를 호출하지 않아야 한다.
- `--build-step` is an opt-in flag; absent means sample-only.
- STEP stage reporting은 manifest data contract가 아니라 operator-facing stdout contract다.
- Custom injected exporters remain an in-process test/runtime hook; they are not the default CLI build-step path.
- skip reporting is operator-facing stdout plus manifest `skipped`; it must not create sampled or STEP artifacts for failed attempts.
- `.aedt`는 만들지 않는다.
- manifest object shape는 list fallback 없이 고정한다.
- notebook-visible sampled index는 `entries` 배열 순서를 그대로 쓴다.
- live status line은 stage 경계에서 newline으로 정리한 뒤 다음 info line을 쓰고, interactive terminal이면 마지막 status line을 다시 그려야 한다.
- live status line must never exceed the current terminal width because carriage-return clearing cannot cleanly erase wrapped physical lines.

## 직접 의존
- `peetsfea.type2_sampled`
- `peetsfea.type2_step_export`

## 이 파일을 직접 쓰는 곳
- `entry/build.py`
- human/agent active sample entrypoint

## 관련 테스트
- [test_sample_type2_entry.py](../tests/type2/test_sample_type2_entry.py.md)

## 변경 시 주의점
- manifest config ownership을 `entry/build.py`로 이동시키지 않는다.
- `MAKE_STEP_ON_SAMPLE` policy와 manifest `config.make_step_on_sample`를 어긋나게 만들지 않는다.
- design directory layout을 바꾸면 build replay와 docs를 함께 갱신한다.
