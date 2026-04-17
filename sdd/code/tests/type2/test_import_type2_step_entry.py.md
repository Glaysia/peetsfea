---
title: test_import_type2_step_entry.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - type2
  - hfss-import
---

# test_import_type2_step_entry.py

## Source
- Path: `tests/type2/test_import_type2_step_entry.py`
- Code note path: `sdd/code/tests/type2/test_import_type2_step_entry.py.md`
- Related plan: [[sdd/plans/0.2.22-type2-import-ledger-pipeline]]
- Tested source: [[sdd/code/entry/import_type2_step.py]]

## 역할
- Type2 import CLI dispatcher가 exporter와 importer를 올바른 순서로 호출하는지 fake callables로 검증한다.
- fake importer fixture는 current `Type2ImportedLedger` mandatory keys를 모두 채운다.

## 입력 / 출력
- 입력:
  - parsed CLI args
  - fake exporter/importer callables
- 출력:
  - fake call history
  - returned `Type2ImportedLedger`

## Canonical state
- Test-local call history lists are the canonical assertion target.

## Invariants / fail-fast
- Default mode calls exporter before importer.
- `--ledger` mode skips exporter and imports the provided ledger path.
- CLI path args are passed through as `Path` values.
- dispatcher-related fixture docs는 STEP ledger의 canonical `em_policy`와 imported ledger의 `boundary`를 구분해 runtime contract drift를 숨기지 않는다.

## 직접 의존
- [[sdd/code/entry/import_type2_step.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 이 파일을 쓰는 곳
- Default pure-Python test suite.

## 관련 테스트
- This file is the direct test coverage for [[sdd/code/entry/import_type2_step.py]].

## 변경 시 주의점
- Do not patch in real STEP export or AEDT launch here.
- STEP ledger policy field를 문서에서 `import_time_policy`로 승격하지 않는다. canonical docs는 `em_policy` 기준이며 runtime fix는 후속 코드 작업이다.
- If CLI defaults or argument names change, these dispatcher assertions must change together.
