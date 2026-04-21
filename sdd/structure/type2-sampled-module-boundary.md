---
title: type2 sampled module boundary
created: 2026-04-21 @ 23:40
updated: 2026-04-21 @ 23:40
tags:
  - sdd
  - structure
  - sampling
---

# type2 sampled module boundary

## 목표
- `src/peetsfea/type2_sampled.py`의 800+ 라인 초과 상태를 ownership 기반으로 분리한다.
- 외부 import 경로는 유지하고 내부 책임만 분할한다.

## ownership 경계
- `src/peetsfea/type2_sampled.py`
  - manifest document/config I/O
  - sampled TOML 파일 생성 orchestration
  - build preparation (`prepare_type2_build`, `prepared_builds_from_manifest`)
  - runtime/entry에서 직접 참조하는 public facade
- `src/peetsfea/type2_sampled_sampling.py`
  - sampled owner path resolution
  - deterministic candidate selection
  - type2 constraints parsing/evaluation
  - tx_rect_void_columns mode-aware sampled owner 계산

## 공개 계약
- canonical public import surface는 계속 `peetsfea.type2_sampled`다.
- `entry/sample.py`, `entry/build.py`, `src/peetsfea/type2_runtime.py`, `tests/type2/*`는 기본적으로 기존 import 경로를 유지한다.
- 분리 모듈은 내부 ownership을 위한 구현 경계로 취급한다.

## 관련 문서
- [[sdd/plans/0.2.22-type2-sampled-build-split]]
- [[sdd/code/src/peetsfea/type2_sampled.py]]
- [[sdd/code/src/peetsfea/type2_sampled_sampling.py]]
