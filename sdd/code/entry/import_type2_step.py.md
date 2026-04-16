# import_type2_step.py

## Source
- Path: `entry/import_type2_step.py`
- Code note path: `sdd/code/entry/import_type2_step.py.md`
- Related plan: [[sdd/plans/0.2.22-type2-import-ledger-pipeline]]
- Runtime module: [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 역할
- Type2 STEP export와 HFSS import+ledger runtime을 연결하는 CLI entrypoint다.
- 기본 모드에서는 fresh type2 STEP ledger를 생성한 뒤 import한다.
- `--ledger` 모드에서는 existing STEP ledger를 그대로 import한다.

## 입력 / 출력
- 기본 입력:
  - `examples/type2.toml`
  - `entry/generate_type2_step.py`
- 기본 출력:
  - `run/step/type2/type2_step_ledger.json`
  - `run/aedt/type2_step_import/type2_import.aedt`
  - `run/aedt/type2_step_import/type2_imported_ledger.json`
- 실행 예:
  - `cd run && ../.venv/bin/python ../entry/import_type2_step.py`
  - `cd run && ../.venv/bin/python ../entry/import_type2_step.py --ledger ../run/step/type2/type2_step_ledger.json`

## Canonical state
- Module-level mutable state는 없다.
- CLI args select whether the STEP ledger is generated fresh or provided explicitly.
- Canonical import behavior lives in [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]].

## Invariants / fail-fast
- `--ledger` mode must not invoke the exporter.
- Default mode must invoke the exporter before importer.
- The importer remains headless and fail-fast through the runtime module.

## 직접 의존
- `entry.generate_type2_step.export_type2_step_artifacts`
- `peetsfea.backend.pyaedt.type2_step_import_pipeline.import_type2_step_ledger`

## 이 파일을 쓰는 곳
- Human/agent opt-in type2 import validation entrypoint.
- [[sdd/code/tests/type2/test_import_type2_step_entry.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_import_type2_step_entry.py]]

## 변경 시 주의점
- Existing type1 build/sample entrypoints must remain untouched.
- If exporter output paths change, defaults here and tests must change together.
