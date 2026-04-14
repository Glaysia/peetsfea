# test_tx_rect_void_step_import_smoke.py

## Source
- Path: `tests/backend_em/test_tx_rect_void_step_import_smoke.py`
- Code note path: `sdd/code/tests/backend_em/test_tx_rect_void_step_import_smoke.py.md`
- Related plan: [[sdd/plans/0.2.22-type2-pyaedt-step-import]]
- Related umbrella plan: [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]]
- Related type2 architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- `import_tx_rect_void_step_to_hfss` modeled import smoke path를 AEDT launch 없이 fake sessions로 검증한다.
- metadata single-entry contract, import diff fail-fast, adapter integration point를 pure-Python으로 방어한다.

## 입력 / 출력
- pytest tests under `tests/backend_em`
- fake HFSS modeler/desktop/session and fake adapter callables
- no AEDT process launch, no real solve

## Canonical state
- test-local fake objects가 import/save/release 호출 이력을 보관한다.
- canonical assertion target은 smoke 함수 반환 payload와 fail-fast 예외다.

## Invariants / fail-fast
- metadata 파일이 없으면 HFSS launch 전에 raise해야 한다.
- `import_3d_cad(False)`는 즉시 raise해야 한다.
- import diff duplicate는 즉시 raise해야 한다.
- happy path에서 adapter는 `modeled_objects[0]`와 diff object names를 입력으로 받아 imported ledger entry를 반환해야 한다.
- desktop release는 실패 케이스에서도 호출되어야 한다.

## 직접 의존
- `pytest`
- `examples.type2.import_tx_rect_void_step_to_hfss`
- `types.ModuleType` (default adapter module import 경로 fake 주입)

## 이 파일을 쓰는 곳
- default/test command path only.

## 관련 테스트
- This file is the direct test note target for [[sdd/code/examples/type2/import_tx_rect_void_step_to_hfss.py]].

## 변경 시 주의점
- real AEDT launch를 추가하면 pure-Python smoke 역할을 깨므로 금지한다.
- adapter contract가 변하면 fake adapter payload와 assertions를 함께 갱신해야 한다.
