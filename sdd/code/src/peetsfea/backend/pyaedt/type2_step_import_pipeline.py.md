# type2_step_import_pipeline.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py.md`
- Related plan: [[sdd/plans/0.2.22-type2-import-ledger-pipeline]]
- Related architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]
- Collaborator: [[sdd/code/src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py]]

## 역할
- Type2 STEP export ledger를 headless HFSS 세션에 import하고 imported AEDT object ledger를 만든다.
- Combined non-model scene STEP와 single `tx_single_coil` modeled object를 같은 import transaction 안에서 처리한다.
- Import 직후 non-model scene objects의 visual state와 modeled TX body의 material/color state를 canonical metadata 기준으로 고정한다.
- `tx_region` canonical coordinates를 사용해 imported TX를 region 내부로 이동시킨다.

## 입력 / 출력
- 입력:
  - `run/step/type2/type2_step_ledger.json`
  - HFSS session factory
- 추가 입력:
  - 이미 열린 `HfssSession` (`import_type2_step_ledger_into_hfss`)
- 출력:
  - `run/aedt/type2_step_import/type2_import.aedt`
  - `run/aedt/type2_step_import/type2_imported_ledger.json`
  - `Type2ImportedLedger`

## Canonical state
- Module-level mutable state는 없다.
- Canonical role/coordinate/terminal source는 STEP export ledger다.
- AEDT runtime에서 읽는 canonical value는 import diff로 얻은 `imported_object_names`뿐이다.
- Combined non-model ledger entry의 `member_objects`가 `tx_region` placement source를 소유한다.

## Invariants / fail-fast
- STEP ledger와 모든 referenced STEP file은 HFSS launch 전에 존재해야 한다.
- `non_model_objects`는 비어 있으면 안 된다.
- prototype `modeled_objects`는 정확히 1개여야 하며 `role == tx_single_coil`이어야 한다.
- type2 object id는 non-model/modeled 전체에서 중복되면 안 된다.
- Combined non-model ledger entry는 `member_objects`를 가져야 하며 `tx_region` member object는 정확히 1개여야 한다.
- 각 STEP import diff는 non-empty, duplicate-free여야 한다.
- `import_3d_cad`, `set_object_model_state`, `save_project`, `release_desktop`의 `False` return은 즉시 raise한다.
- Non-model object는 `model=False`, modeled object는 `model=True`로 명시 고정한다.
- Combined non-model scene STEP may produce multiple HFSS objects from one import diff, and they all stay owned by the single non-model ledger entry.
- Imported non-model objects are colored gray with transparency immediately after import.
- Imported TX bodies are ordered by `expected_exported_body_names`; PCB bodies become `FR4_epoxy`/green and copper bodies become `copper`/copper-color.
- TX outer bounds must fit inside `tx_region`; placement uses export-ledger coordinates only and never AEDT reverse-calculation.
- `import_type2_step_ledger_into_hfss`는 import/save까지만 수행하고 desktop release ownership을 호출자에게 남긴다.

## 직접 의존
- `peetsfea.aedt.Hfss`
- `peetsfea.aedt.protocols`
- `peetsfea.aedt.failfast`
- `peetsfea.backend.pyaedt.type2_modeled_import_adapter`

## 이 파일을 쓰는 곳
- [[sdd/code/entry/import_type2_step.py]]
- `notebooks/view_type2_hfss_import.ipynb`
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]
- [[sdd/code/tests/type2/test_import_type2_step_entry.py]]

## 변경 시 주의점
- Imported ledger schema를 바꾸면 CLI, tests, architecture, downstream EM adapter 계획을 함께 갱신한다.
- EM pipeline 연결은 이 파일에 섞지 말고 별도 adapter/plan으로 추가한다.
- AEDT geometry에서 coordinates나 terminal semantics를 역산하지 않는다.
