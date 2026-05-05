---
title: import_non_model_step_to_hfss.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - hfss-import
  - aedt
---

# import_non_model_step_to_hfss.py

## Source
- Path: `entry/import_non_model_step_to_hfss.py`
- Code note path: `sdd/code/entry/import_non_model_step_to_hfss.py.md`
- Related plan: [0.2.22-type2-step-to-em-validate-pipeline](../../plans/0.2.22-type2-step-to-em-validate-pipeline.md)
- Related umbrella plan: [0.2.22-type2-step-to-em-validate-pipeline](../../plans/0.2.22-type2-step-to-em-validate-pipeline.md)
- Related type2 architecture: [type2-step-to-em-validate-pipeline](../../architecture/type2-step-to-em-validate-pipeline.md)

## 역할
- type2 non-model STEP artifact를 headless HFSS 세션에 import하는 opt-in smoke script다.
- runtime manifest/build dispatch와 분리된 AEDT import 검증 경로만 담당한다.

## 입력 / 출력
- 입력: `run/step/type2/type2_non_model_scene.step`
- 출력: `run/aedt/type2_step_import_smoke/type2_non_model_scene_import.aedt`
- CLI entry: `../.venv/bin/python ../entry/import_non_model_step_to_hfss.py` from `run/`
- 반환: `Type2StepImportResult` with step path, AEDT path, imported object names

## Canonical state
- module-level mutable state는 없다.
- canonical imported object ledger는 import 전후 `modeler.object_names`의 deterministic diff다.

## Invariants / fail-fast
- STEP 파일이 없으면 HFSS를 launch하지 않고 `FileNotFoundError`를 raise한다.
- PyAEDT `import_3d_cad`, `set_object_model_state`, `save_project`, `release_desktop` false return은 즉시 raise한다.
- import 후 새 object name diff가 비어 있으면 `RuntimeError`를 raise한다.
- imported object name은 non-empty AEDT name으로 검증한다.

## 직접 의존
- `pathlib.Path`
- `typing.Protocol`, `TypedDict`
- `peetsfea.aedt.Hfss`
- `peetsfea.aedt.failfast`

## 이 파일을 쓰는 곳
- 사람이 직접 실행하는 type2 STEP-to-HFSS smoke path다.
- [test_type2_step_import_smoke.py](../tests/backend_em/test_type2_step_import_smoke.py.md)가 fake HFSS factory로 pure-Python 계약을 방어한다.

## 관련 테스트
- [test_type2_step_import_smoke.py](../tests/backend_em/test_type2_step_import_smoke.py.md)
- Real AEDT validation is opt-in and not part of default tests.

## 변경 시 주의점
- runtime build flow에 연결하려면 새 계획을 만들고 manifest/type dispatch 설계를 먼저 갱신한다.
- full STEP-to-EM validation flow에 연결하려면 [0.2.22-type2-step-to-em-validate-pipeline](../../plans/0.2.22-type2-step-to-em-validate-pipeline.md)의 object-level ledger와 `EmPipelineInput` adapter 계약을 먼저 구현한다.
- PyAEDT 버전이 올라가 `input_file_unit` 같은 새 인자를 쓰게 되면 [0.2.22-type2-step-to-em-validate-pipeline](../../plans/0.2.22-type2-step-to-em-validate-pipeline.md)를 갱신한다.
- 출력 STEP artifact 경로를 바꾸면 [0.2.22-type2-build123d-non-model-step](../../plans/0.2.22-type2-build123d-non-model-step.md)와 viewer registry도 같이 확인한다.
