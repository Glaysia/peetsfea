---
title: test_sample_type2_entry.py
created: 2026-04-18 @ 09:09
updated: 2026-04-19 @ 18:05
tags:
  - sampling
  - test
---

# test_sample_type2_entry.py

## Source
- Path: `tests/type2/test_sample_type2_entry.py`
- Code note path: `sdd/code/tests/type2/test_sample_type2_entry.py.md`
- Tested source:
  - [[sdd/code/entry/sample.py]]
  - [[sdd/code/src/peetsfea/type2_sampled.py]]
  - [[sdd/code/src/peetsfea/type2_runtime.py]]

## 역할
- active sample entry가 manifest object, frozen sampled TOML, optional STEP handoff를 올바르게 만드는지 검증한다.

## Canonical state
- sampled metadata table, manifest `config`, per-design future artifact path가 canonical assertion surface다.

## Invariants / fail-fast
- source `count != 1` owner만 sampled metadata에 기록되어야 한다.
- sampled owner range는 전부 `count=1`로 frozen 되어야 한다.
- fixed owner는 sampled metadata에 들어가지 않아야 한다.
- `make_step_on_sample`이 `false`면 exporter가 호출되지 않아야 한다.
- sample 단계는 `.aedt`를 만들지 않아야 한다.
- fixed `wall_parallel_stack_present`는 sampled metadata owner list에 들어가면 안 된다. frozen sampled TOML은 source fixed contract `[true, 1, 1, 1]`를 그대로 유지해야 한다.
- fixed `rx_plate_stack` scalar fields도 sampled metadata owner list에 들어가면 안 되며, frozen sampled TOML에 값 그대로 남아야 한다.

## 관련 테스트
- This file is the direct test coverage for the active sample entry split.

## 변경 시 주의점
- full HFSS runtime assertion을 이 파일에 섞지 않는다.
