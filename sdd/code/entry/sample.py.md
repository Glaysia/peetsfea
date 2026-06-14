---
title: sample.py
created: 2026-04-17 @ 09:09
updated: 2026-06-01
tags:
  - sampling
  - step
---

# entry/sample.py

- Source path: `entry/sample.py`
- Code note path: `sdd/code/entry/sample.py.md`
- Related plan: [0.3.0 minimal step two port reset](../../plans/0.3.0-minimal-step-two-port-reset.md)
- Collaborators:
  - [minimal_step.py](../src/peetsfea/minimal_step.py.md)

## 역할
- active 0.3.0 minimal sample entrypoint다.
- non-model-only source TOML을 단일 sampled design directory로 복사한다.
- sampled directory 안에 minimal STEP과 minimal ledger를 생성한다.
- sampled dimension count는 0으로 고정한다.

## 입력 / 출력
- 입력: `examples/minimal_step_two_port.toml`
- 출력:
  - `run/sampled/minimal/manifest.json`
  - `run/sampled/minimal/<design_id>/sampled.toml`
  - `run/sampled/minimal/<design_id>/<design_id>.source.toml`
  - `run/sampled/minimal/<design_id>/<design_id>.repro.toml`
  - `run/sampled/minimal/<design_id>/<design_id>.dataset.toml`
  - `run/sampled/minimal/<design_id>/minimal_scene.step`
  - `run/sampled/minimal/<design_id>/minimal_step_ledger.json`

## Canonical state
- Manifest JSON is the handoff state for `entry/build.py`.
- Design ID is a hash of source TOML bytes plus seed.

## Invariants / fail-fast
- Missing or invalid source TOML raises through `export_minimal_step_artifacts`.
- This entrypoint does not start AEDT.
- It does not expose old type2 sampling, geometry, or worker pools.

## 관련 테스트
- [test_minimal_step.py](../tests/test_minimal_step.py.md)

## 변경 시 주의점
- Do not add fallback compatibility for old type2 manifests.
