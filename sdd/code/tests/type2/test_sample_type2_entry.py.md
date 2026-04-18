---
title: test_sample_type2_entry.py
created: 2026-04-18 @ 09:09
updated: 2026-04-18 @ 23:24
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
- active sample entry가 manifest object, frozen sampled TOML, STEP artifact handoff를 올바르게 만드는지 검증한다.

## Canonical state
- sampled metadata table, manifest `config`, per-design STEP path가 canonical assertion surface다.

## Invariants / fail-fast
- source `count != 1` owner만 sampled metadata에 기록되어야 한다.
- sampled owner range는 전부 `count=1`로 frozen 되어야 한다.
- fixed owner는 sampled metadata에 들어가지 않아야 한다.
- sample 단계는 `.aedt`를 만들지 않아야 한다.

## 관련 테스트
- This file is the direct test coverage for the active sample entry split.

## 변경 시 주의점
- full HFSS runtime assertion을 이 파일에 섞지 않는다.
