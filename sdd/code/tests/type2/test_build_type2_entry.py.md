---
title: test_build_type2_entry.py
created: 2026-04-18 @ 09:09
updated: 2026-04-18 @ 23:24
tags:
  - build
  - test
---

# test_build_type2_entry.py

## Source
- Path: `tests/type2/test_build_type2_entry.py`
- Code note path: `sdd/code/tests/type2/test_build_type2_entry.py.md`
- Tested source:
  - [[sdd/code/entry/build.py]]
  - [[sdd/code/src/peetsfea/type2_sampled.py]]
  - [[sdd/code/src/peetsfea/type2_runtime.py]]

## 역할
- active build entry의 manifest config read, STEP-ledger preflight, design variable handoff를 검증한다.

## Canonical state
- prepared sampled build input과 runner call payload가 canonical assertion surface다.

## Invariants / fail-fast
- list manifest는 즉시 실패해야 한다.
- missing `config.aedt_builder_n`는 즉시 실패해야 한다.
- missing step ledger는 runner 전에 즉시 실패해야 한다.
- runner에는 sampled metadata-derived design variables만 전달되어야 한다.

## 변경 시 주의점
- full AEDT runtime regression을 이 파일에서 다시 구현하지 않는다.
