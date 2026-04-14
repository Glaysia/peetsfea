# Type2 STEP to EM Validate Pipeline

이 문서는 type2 object-level STEP artifact에서 EM validation까지 이어지는 ownership handoff를 설명한다. 상위 계획은 [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]]다.

## Boundary
- 입력 SSOT는 type2 object registry/TOML-derived geometry object set이다.
- geometry authoring은 build123d가 담당하고, Ansys/HFSS는 headless PyAEDT import 이후 EM setup과 validation을 담당한다.
- object-level STEP artifact와 artifact ledger가 build123d와 PyAEDT 사이의 경계다.
- `EmPipelineInput`이 imported AEDT object ledger와 기존 EM pipeline 사이의 경계다.
- 출력은 imported AEDT object ledger, EM pipeline result, repo validation report, AEDT `ValidateDesign()` 결과다.

## Flow
1. Type2 object registry가 object id, role, material, canonical coordinates, model/non-model intent를 확정한다.
2. Build123d export 단계가 object마다 STEP artifact를 만들고 ledger에 `object_id`, `role`, `step_path`, `expected_model_state`를 기록한다.
3. Headless HFSS import 단계가 STEP artifact를 하나씩 import하고, import 전후 `modeler.object_names` diff를 검증해 `imported_object_names`를 ledger에 추가한다.
4. Import adapter가 ledger의 `em_mapping_role`를 읽어 `EmPipelineInput.ready_objects`, `ports`, `context`, `endpoints`를 조립한다.
5. `run_em_pipeline()`가 grouping, series/subtract metadata, radiation boundary, explicit ports, source phase, analysis setup, post template creation을 수행한다.
6. `validate_pipeline()`가 repo-level TX/RX conductor readiness를 검사하고, AEDT `ValidateDesign()`가 design-level validation을 수행한다.

## tx_rect_void Prototype Bridge
- prototype export의 canonical source는 metadata JSON의 `modeled_objects[0]`다.
- prototype import의 runtime source는 headless HFSS import 결과의 `imported_object_names`다.
- single-coil prototype 단계의 handoff는 아래 2단으로 고정한다:
  1. `modeled_objects[0]`에서 `object_id`, `role`, `material`, `model_state`, `step_path`, canonical coordinates, terminal metadata를 읽는다.
  2. import 전후 `modeler.object_names` diff에서 얻은 `imported_object_names`를 같은 modeled object의 runtime-import 결과로 붙인다.

### Matching Rules
- `tx_rect_void` prototype metadata는 정확히 single-entry `modeled_objects`여야 한다.
- 그 single entry의 `role`은 `tx_single_coil`이어야 한다.
- metadata `step_path`는 실제 import input STEP와 일치해야 한다.
- import diff로 얻은 모든 `imported_object_names`는 그 single modeled object에 귀속된다.
- object role, coordinates, terminal meaning은 metadata에서 읽고, imported object names만 import 결과에서 읽는다.
- AEDT live geometry를 다시 측정해 role, coordinates, terminal semantics를 역산하지 않는다.

### Fail-fast
- `modeled_objects` 길이가 1이 아니면 즉시 실패한다.
- `role != tx_single_coil`이면 즉시 실패한다.
- metadata `step_path`와 실제 import input이 다르면 즉시 실패한다.
- import diff가 비어 있으면 즉시 실패한다.
- import diff에 duplicate imported names가 있으면 즉시 실패한다.

### Intentionally Unresolved
- `em_mapping_role`
- `EmPipelineInput.ready_objects` 분류 규칙
- port assignment
- multi-object composition
- global placement transform

## Invariants
- 하나의 type2 object id는 하나의 canonical STEP artifact entry만 가진다.
- imported object role과 coordinates는 생성 시점 metadata와 ledger에서 읽는다. AEDT 내부 geometry에서 역산하지 않는다.
- imported object diff가 비어 있거나 중복 이름을 만들면 즉시 실패한다.
- `EmPipelineInput`은 TX/RX conductor와 explicit port 계약을 만족해야 하며, 그렇지 않으면 `run_em_pipeline()` 또는 `validate_pipeline()`가 fail-fast로 멈춘다.
- PyAEDT `import_3d_cad`, `set_object_model_state`, `save_project`, EM setup calls, `ValidateDesign()`의 `False` return은 모두 즉시 예외다.
- GUI-visible AEDT는 이 흐름의 검증 경로가 아니다.

## Related Code Notes
- [[sdd/code/examples/type2/generate_non_model_step.py]]
- [[sdd/code/examples/type2/import_non_model_step_to_hfss.py]]
- [[sdd/code/src/peetsfea/aedt/wrappers.py]]
- [[sdd/code/src/peetsfea/aedt/protocols.py]]
- [[sdd/code/tests/backend_em/test_type2_step_import_smoke.py]]

## Related Plans / Diagrams
- [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]]
- [[sdd/plans/0.2.22-type2-build123d-non-model-step]]
- [[sdd/plans/0.2.22-type2-pyaedt-step-import]]
- [[sdd/diagrams/type2-step-to-em-validate-flow]]
- [[sdd/structure/sdd-vault-layout]]
