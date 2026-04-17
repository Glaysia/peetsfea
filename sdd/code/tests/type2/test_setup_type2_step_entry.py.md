---
title: test_setup_type2_step_entry.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 23:30
tags:
  - type2
  - hfss-import
  - em
---

# test_setup_type2_step_entry.py

## Source
- Path: `tests/type2/test_setup_type2_step_entry.py`
- Code note path: `sdd/code/tests/type2/test_setup_type2_step_entry.py.md`
- Tested source: [[sdd/code/entry/setup_type2_step.py]]

## 역할
- setup-ready entry dispatcher가 exporter와 runtime을 올바른 순서로 호출하는지 검증한다.
- headless helper와 attached helper가 code-owned orchestration surface로 유지되는지 검증한다.

## 입력 / 출력
- 입력:
  - parsed CLI args
  - fake exporter/runtime callables
- 출력:
  - fake call history
  - fake setup-ready result

## Canonical state
- test-local call history가 canonical assertion surface다.

## Invariants / fail-fast
- default mode는 exporter 후 runtime 호출이다.
- `--ledger` mode는 exporter를 건너뛴다.
- notebook은 this entry/runtime helper의 thin consumer다.

## 직접 의존
- [[sdd/code/entry/setup_type2_step.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]

## 이 파일을 쓰는 곳
- Default pure-Python test suite.

## 관련 테스트
- This file is the direct test coverage for [[sdd/code/entry/setup_type2_step.py]].

## 변경 시 주의점
- real STEP export or AEDT launch를 넣지 않는다.
- import-only entry assertions와 setup-ready entry assertions를 섞지 않는다.
