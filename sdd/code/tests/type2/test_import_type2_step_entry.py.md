# test_import_type2_step_entry.py

## Source
- Path: `tests/type2/test_import_type2_step_entry.py`
- Code note path: `sdd/code/tests/type2/test_import_type2_step_entry.py.md`
- Related plan: [[sdd/plans/0.2.22-type2-import-ledger-pipeline]]
- Tested source: [[sdd/code/entry/import_type2_step.py]]

## 역할
- Type2 import CLI dispatcher가 exporter와 importer를 올바른 순서로 호출하는지 fake callables로 검증한다.

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

## 직접 의존
- [[sdd/code/entry/import_type2_step.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 이 파일을 쓰는 곳
- Default pure-Python test suite.

## 관련 테스트
- This file is the direct test coverage for [[sdd/code/entry/import_type2_step.py]].

## 변경 시 주의점
- Do not patch in real STEP export or AEDT launch here.
- If CLI defaults or argument names change, these dispatcher assertions must change together.
