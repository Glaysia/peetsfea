---
title: test_import_type2_step_entry.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 00:20
tags:
  - type2
  - hfss-import
---

# test_import_type2_step_entry.py

## Source
- Path: `tests/type2/test_import_type2_step_entry.py`
- Code note path: `sdd/code/tests/type2/test_import_type2_step_entry.py.md`
- Tested source: [[sdd/code/entry/import_type2_step.py]]

## 역할
- import-only entry dispatcher가 exporter와 importer를 올바른 순서로 호출하는지 검증한다.

## 입력 / 출력
- 입력:
  - parsed CLI args
  - fake exporter/importer callables
- 출력:
  - fake call history
  - fake import-only result

## Canonical state
- test-local call history lists are the canonical assertion target.

## Invariants / fail-fast
- default mode는 exporter 후 importer를 호출한다.
- `--ledger` mode는 exporter를 건너뛴다.
- import-only result fixture는 `mesh`/`boundary` 없이 current `Type2ImportedLedger` shape만 채운다.

## 직접 의존
- [[sdd/code/entry/import_type2_step.py]]

## 이 파일을 쓰는 곳
- Default pure-Python test suite.

## 관련 테스트
- setup-ready entry coverage lives in [[sdd/code/tests/type2/test_setup_type2_step_entry.py]].

## 변경 시 주의점
- import-only entry를 setup-ready owner로 다시 확장하지 않는다.
