# test_type2_step_import_pipeline.py

## Source
- Path: `tests/backend_em/test_type2_step_import_pipeline.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_step_import_pipeline.py.md`
- Related plan: [[sdd/plans/0.2.22-type2-import-ledger-pipeline]]
- Tested source: [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 역할
- Type2 STEP import+ledger runtime을 AEDT launch 없이 fake HFSS session으로 검증한다.

## 입력 / 출력
- 입력:
  - test-local STEP placeholder files
  - test-local type2 STEP ledger JSON
  - fake modeler/desktop/HFSS sessions
- 출력:
  - runtime return ledger
  - written imported ledger JSON
  - fake call histories

## Canonical state
- Test-local fake modeler owns import call order, object name batches, and model-state call history.
- The written imported ledger JSON must match runtime result.

## Invariants / fail-fast
- Non-model imports happen before modeled imports.
- Non-model objects are assigned `model=False`; modeled objects are assigned `model=True`.
- Missing STEP path and malformed ledger fail before HFSS launch when possible.
- Duplicate object id, empty import diff, duplicate imported names, import `False`, and save `False` all raise.
- Desktop release is attempted when import fails after launch.

## 직접 의존
- `pytest`
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 이 파일을 쓰는 곳
- Default pure-Python test suite.

## 관련 테스트
- This file is the direct test coverage for [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]].

## 변경 시 주의점
- Do not introduce real AEDT launch here.
- If imported ledger schema changes, fake ledger builders and assertions must change together.
