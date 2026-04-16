# import_tx_rect_void_step_to_hfss.py

## Source
- Path: `examples/type2/import_tx_rect_void_step_to_hfss.py`
- Code note path: `sdd/code/examples/type2/import_tx_rect_void_step_to_hfss.py.md`
- Related plan: [[sdd/plans/0.2.22-type2-pyaedt-step-import]]
- Related umbrella plan: [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]]
- Related type2 architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- `type2.toml`에서 생성된 `tx_single_coil` modeled STEP artifact를 headless HFSS 세션에 import하는 opt-in smoke script다.
- metadata JSON의 `modeled_objects[0]`와 runtime import diff `imported_object_names`를 어댑터에 전달해 imported modeled ledger entry를 만든다.
- `EmPipelineInput`, port/source/solve 단계는 다루지 않는다.

## 입력 / 출력
- 기본 입력:
  - `examples/type2/type2.toml`
  - `examples/type2/generate_type2_step.py` (artifact가 없을 때 1회 호출)
- 기본 artifact 해석 규칙:
  - `source_toml_path == examples/type2/type2.toml`
  - `modeled_objects` single-entry
  - `modeled_objects[0].role == tx_single_coil`
- 출력 AEDT: `run/aedt/type2_step_import_smoke/type2_tx_single_coil_import.aedt`
- CLI entry: `../.venv/bin/python ../examples/type2/import_tx_rect_void_step_to_hfss.py` from `run/`
- 반환:
  - `import_result` (`step_path`, `metadata_path`, `aedt_path`, `imported_object_names`)
  - `imported_modeled_object_entry` (adapter output ledger entry)

## Canonical state
- module-level mutable state는 없다.
- canonical modeled source는 `type2.toml`에서 파생된 metadata JSON `modeled_objects[0]`다.
- canonical runtime import source는 HFSS import 전후 `modeler.object_names` diff다.

## Invariants / fail-fast
- 기본 경로(auto)에서 artifact가 없으면 `generate_type2_step.py`를 먼저 실행하고 재해석한다.
- 재해석 뒤에도 `type2.toml` 기반 `tx_single_coil` artifact를 찾지 못하면 즉시 raise한다.
- explicit STEP/metadata 입력이 오면 두 값을 모두 요구한다(한쪽만 전달 금지).
- metadata는 `modeled_objects` single-entry를 강제하고 `role == tx_single_coil`, `step_path` 문자열 일치를 강제한다.
- metadata의 expected exported body names/count를 검증하고 import diff 수가 expected count와 다르면 즉시 실패한다.
- PyAEDT `import_3d_cad`, `save_project`, `release_desktop` false return은 즉시 raise한다.
- import diff가 비거나 duplicate면 즉시 raise한다.
- adapter output은 required fields와 `imported_object_names`/`step_path` 일치를 검증한다. `imported_object_names`는 list/tuple 같은 문자열 시퀀스를 허용한다.

## 직접 의존
- `pathlib.Path`
- `typing.Protocol`, `TypedDict`
- `peetsfea.aedt.Hfss`
- `peetsfea.aedt.failfast`
- `peetsfea.backend.pyaedt.type2_modeled_import_adapter.build_single_imported_modeled_object_entry`

## 이 파일을 쓰는 곳
- 사람이 직접 실행하는 modeled STEP-to-HFSS smoke path다.
- [[sdd/code/tests/backend_em/test_tx_rect_void_step_import_smoke.py]]가 fake HFSS/adapter로 pure-Python 계약을 방어한다.

## 관련 테스트
- [[sdd/code/tests/backend_em/test_tx_rect_void_step_import_smoke.py]]
- Real AEDT validation is opt-in and not part of default tests.

## 변경 시 주의점
- adapter 함수 시그니처를 바꾸면 이 smoke script의 loader/call site를 같이 갱신해야 한다.
- type2 exporter script path나 metadata ledger shape가 바뀌면 이 smoke script의 auto-resolver 규칙도 함께 갱신해야 한다.
- prototype 단계에서 geometry reverse-calculation을 추가하지 않는다. 좌표/terminal semantics는 metadata source를 유지한다.
- scope 확장(ports/sources/solve, multi-coil)은 [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]] 결정 이후에만 진행한다.
