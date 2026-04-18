---
title: type2_runtime.py
created: 2026-04-18 @ 23:24
updated: 2026-04-18 @ 23:24
tags:
  - runtime
  - type2
---

# type2_runtime.py

## Source
- Path: `src/peetsfea/type2_runtime.py`
- Code note path: `sdd/code/src/peetsfea/type2_runtime.py.md`
- Related plan: [[sdd/plans/0.2.23-type2-sampled-build-split]]
- Collaborators:
  - [[sdd/code/entry/sample.py]]
  - [[sdd/code/entry/build.py]]
  - [[sdd/code/src/peetsfea/type2_sampled.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]

## 역할
- active type2 operator surface가 공유하는 process-pool orchestration helper다.
- sample-side STEP export와 build-side AEDT replay를 분리된 함수로 제공한다.
- entry layer의 fail-fast preflight를 한 곳에 고정한다.

## 입력 / 출력
- 입력:
  - `PreparedType2Build` tuple
  - parallel worker count
- 출력:
  - per-design STEP artifact summary
  - per-design AEDT artifact summary

## Canonical state
- worker input canonical unit은 `PreparedType2Build`다.
- sample-side helper는 sampled TOML path에서 STEP export target path를 읽는다.
- build-side helper는 existing `step_ledger_path`를 읽어 AEDT output path를 계산하지 않고 그대로 사용한다.

## Invariants / fail-fast
- worker count는 양수여야 한다.
- build-side preflight는 모든 `step_ledger_path` 존재를 HFSS 시작 전에 검증해야 한다.
- custom exporter/runner injection이 들어오면 single-process deterministic path를 사용한다.

## 직접 의존
- `entry.generate_type2_step`
- `peetsfea.type2_sampled`
- `peetsfea.backend.pyaedt.type2_step_setup_ready`

## 이 파일을 쓰는 곳
- `entry/sample.py`
- `entry/build.py`

## 관련 테스트
- [[sdd/code/tests/type2/test_sample_type2_entry.py]]
- [[sdd/code/tests/type2/test_build_type2_entry.py]]

## 변경 시 주의점
- STEP worker와 AEDT worker를 다시 한 함수에 묶어 per-design mixed stage로 되돌리지 않는다.
- preflight와 actual runner payload가 서로 다른 path contract를 가지지 않게 유지한다.
