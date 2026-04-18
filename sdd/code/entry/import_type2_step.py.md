---
title: import_type2_step.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - hfss-import
---

# import_type2_step.py

## Source
- Path: `entry/import_type2_step.py`
- Code note path: `sdd/code/entry/import_type2_step.py.md`
- Runtime module: [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 역할
- type2 export + import-only runtime을 연결하는 CLI entrypoint다.
- setup-ready owner는 [[sdd/code/entry/setup_type2_step.py]]로 분리됐다.

## 입력 / 출력
- 기본 입력:
  - `examples/type2_fixed.toml`
  - `entry/generate_type2_step.py`
- 기본 출력:
  - `run/step/type2/type2_step_ledger.json`
  - `run/aedt/type2_step_import/type2_import.aedt`
  - `run/aedt/type2_step_import/type2_imported_ledger.json`

## Canonical state
- module-level mutable state는 없다.
- code-owned orchestration surface는 `export_and_import_type2_step(...)`와 `export_and_import_type2_step_into_hfss(...)`다.

## Invariants / fail-fast
- `--ledger` mode는 exporter를 호출하지 않는다.
- default mode는 exporter 후 import-only runtime을 호출한다.
- CLI는 import-only ledger count/path만 출력한다. mesh/boundary summary는 이 entry의 contract가 아니다.

## 직접 의존
- [[sdd/code/entry/generate_type2_step.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 이 파일을 쓰는 곳
- Human/agent opt-in import-only validation entrypoint.

## 관련 테스트
- [[sdd/code/tests/type2/test_import_type2_step_entry.py]]

## 변경 시 주의점
- setup-ready owner surface를 다시 이 entry로 합치지 않는다.
