---
title: type2_sampled.py
created: 2026-04-18 @ 09:09
updated: 2026-04-19 @ 18:05
tags:
  - sampling
  - build
---

# type2_sampled.py

## Source
- Path: `src/peetsfea/type2_sampled.py`
- Code note path: `sdd/code/src/peetsfea/type2_sampled.py.md`
- Related plan: [[sdd/plans/0.2.23-type2-sampled-build-split]]
- Related feature plan: [[sdd/plans/0.2.23-type2-tx-wall-parallel-ferrite-stack]]

## 역할
- type2 sampled flow의 canonical metadata/model/path planning helper다.
- source type2 TOML에서 sampled owner를 선택하고 frozen sampled TOML을 만든다.
- sample manifest document contract, optional sample-side STEP worker contract, notebook index lookup contract, build gate, design variable derivation도 소유한다.

## 입력 / 출력
- 입력:
  - source type2 TOML path
  - seed range
  - sampled TOML path 또는 manifest path
- 출력:
  - `Type2SampleManifestConfig`
  - `Type2SampleManifestDocument`
  - `Type2SampleManifestEntry`
  - `[sampled]` metadata-bearing frozen TOML
  - `PreparedType2Build`

## Canonical state
- sampled metadata table 이름은 `[sampled]`다.
- sampled owner canonical path는 `modeled_objects.<object_id>.<field>`다.
- TX-only `wall_parallel_stack_present`도 sampled owner set의 canonical field가 될 수 있다.
- geometry-only `rx_plate_stack`는 sampled range owner를 갖지 않는다. sampled TOML은 이 object를 source fixed scalar 그대로 복제한다.
- build path planning canonical root는 `run/sampled/type2/<design_id>/` layout이다.
- `design_id`와 folder basename format은 `s{sample_index:06d}_{generated_hash4}_{head_hash4}_{retry_number}`다.
- sample manifest top-level shape는 `config` + `entries` object다.
- sample manifest `config`는 `source_toml_path`, `seed_first`, `seed_n`, `sampler_n`, `make_step_on_sample`, `aedt_builder_n`만 가진다.
- manifest `entries` 순서가 notebook index SSOT다.
- design variable expression contract도 이 module이 source-of-truth다.

## Invariants / fail-fast
- source sample path는 raw source여야 하며 pre-existing `[sampled]` metadata를 가지면 안 된다.
- manifest loader는 old JSON array shape를 허용하지 않는다.
- `make_step_on_sample=True`일 때만 sample generation은 one worker = one sampled TOML + one STEP export contract를 유지한다.
- `sample_index`는 0-based manifest order identity다. `seed`는 provenance only다.
- `head_hash4`는 current `git HEAD` full hash 앞 4자리여야 한다.
- `retry_number`는 현재 baseline에서 `0` 고정이지만 metadata/manifest contract에는 항상 있어야 한다.
- sampled metadata owner list는 source exportable owner set과 exact match여야 한다.
- build input sampled TOML은 modeled range owner 전부가 frozen `count=1`이어야 한다.
- TX `wall_parallel_stack_present`가 sampled source이면 frozen sampled TOML에도 `count=1`로 남아야 하며 sampled metadata owner list에도 포함돼야 한다.
- fixed `rx_plate_stack` scalar fields는 sampled metadata owner list에 나타나면 안 된다.
- design variable unit contract는 int/count, unitless ratio/factor, `_mm` length로만 허용한다.

## 직접 의존
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/spec/toml_render.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_sample_type2_entry.py]]
- [[sdd/code/tests/type2/test_build_type2_entry.py]]

## 변경 시 주의점
- design/folder identity contract를 바꾸면 manifest replay, notebook index selection, build replay가 함께 흔들린다.
- per-design output path naming을 바꾸면 build entry, notebook, docs를 함께 갱신한다.
- 800줄을 넘는 파일이지만 이번 변경은 sampled/build policy toggle과 manifest contract에 국한되므로 ownership split보다 contract 일관성을 우선한다.
