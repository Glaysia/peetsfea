# Type2 STEP to EM Validate Pipeline

이 문서는 `examples/type2.toml`에서 combined non-model scene STEP와 modeled STEP artifact를 거쳐 EM validation까지 이어지는 ownership handoff를 설명한다. 상위 계획은 [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]], type2 TOML 단일화 계획은 [[sdd/plans/0.2.22-type2-toml-unification]]이다.

## Implementation Status
- Import+Ledger 단계는 [[sdd/plans/0.2.22-type2-import-ledger-pipeline]]에서 구현됐다.
- Runtime entry는 [[sdd/code/entry/import_type2_step.py]]이고 core runtime은 [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]다.
- Imported ledger까지가 현재 구현 범위이며, `EmPipelineInput` 조립과 EM validate는 후속 단계다.

## Boundary
- 입력 SSOT는 `examples/type2.toml`이다.
- `type2.toml`은 non-model guide objects와 modeled objects를 같은 object registry 안에서 표현한다.
- geometry authoring은 build123d가 담당하고, Ansys/HFSS는 headless PyAEDT import 이후 EM setup과 validation을 담당한다.
- combined non-model scene STEP, modeled STEP artifact, metadata ledger가 build123d와 PyAEDT 사이의 경계다.
- `EmPipelineInput`이 imported AEDT object ledger와 기존 EM pipeline 사이의 경계다.
- 출력은 imported AEDT object ledger, EM pipeline result, repo validation report, AEDT `ValidateDesign()` 결과다.

## Flow
1. `examples/type2.toml`이 object id, role, material, model_state, canonical coordinates를 확정한다.
2. Type2 parser가 `[[non_model_objects]]`와 `[[modeled_objects]]`를 같은 registry model로 읽는다.
3. Build123d export 단계가 object마다 STEP artifact를 만들고 metadata ledger에 `object_id`, `role`, `material`, `model_state`, `step_path`, canonical coordinates를 기록한다.
4. Headless HFSS import 단계가 STEP artifact를 하나씩 import하고, import 전후 `modeler.object_names` diff를 검증해 `imported_object_names`를 ledger에 추가한다.
5. Import+Ledger runtime이 non-model entries를 `model=False`, modeled entries를 `model=True`로 고정하고 imported ledger JSON을 쓴다.
6. Prototype adapter가 modeled metadata ledger와 `imported_object_names`를 합쳐 imported modeled-object ledger entry를 만든다.
7. Post-prototype adapter가 ledger의 future EM mapping role을 읽어 `EmPipelineInput.ready_objects`, `ports`, `context`, `endpoints`를 조립한다.
8. `run_em_pipeline()`가 grouping, series/subtract metadata, radiation boundary, explicit ports, source phase, analysis setup, post template creation을 수행한다.
9. `validate_pipeline()`가 repo-level TX/RX conductor readiness를 검사하고, AEDT `ValidateDesign()`가 design-level validation을 수행한다.

## Type2 TOML Object Bridge
- `type2.toml`의 `[[non_model_objects]]`는 scene/envelope guide object의 canonical source다.
- `type2.toml`의 `[[modeled_objects]]`는 generated STEP modeled object의 canonical source다.
- 첫 modeled object는 `role = "tx_single_coil"`인 `tx_rect_void` TX coil이다.
- `tx_rect_void` geometry authoring code may be reused internally, but the public input ownership is `type2.toml`.
- Removed split TOML inputs are not type2 public SSOT.

## Prototype Matching Rules
- prototype `type2.toml` must contain exactly one `role = "tx_single_coil"` modeled object.
- import diff로 얻은 모든 `imported_object_names`는 그 single modeled object에 귀속된다.
- object role, coordinates, terminal meaning은 `type2.toml`-derived metadata ledger에서 읽고, imported object names만 import 결과에서 읽는다.
- AEDT live geometry를 다시 측정해 role, coordinates, terminal semantics를 역산하지 않는다.
- prototype adapter 출력에는 아직 EM mapping role이 없다. 이는 post-prototype 조립 단계에서만 추가된다.

## Fail-fast
- `type2.toml`에 unsupported modeled object role이 있으면 즉시 실패한다.
- prototype 단계에서 `tx_single_coil` modeled object count가 1이 아니면 즉시 실패한다.
- metadata `step_path`와 실제 import input이 다르면 즉시 실패한다.
- import diff가 비어 있으면 즉시 실패한다.
- import diff에 duplicate imported names가 있으면 즉시 실패한다.

## Intentionally Unresolved
- EM mapping role taxonomy
- `EmPipelineInput.ready_objects` 분류 규칙
- port assignment
- multi-object / multi-coil composition
- global placement transform

## Invariants
- 하나의 type2 object id는 하나의 canonical object registry owner를 가진다.
- imported object role과 coordinates는 `type2.toml`에서 파생된 metadata ledger에서 읽는다. AEDT 내부 geometry에서 역산하지 않는다.
- imported object diff가 비어 있거나 중복 이름을 만들면 즉시 실패한다.
- `EmPipelineInput`은 TX/RX conductor와 explicit port 계약을 만족해야 하며, 그렇지 않으면 `run_em_pipeline()` 또는 `validate_pipeline()`가 fail-fast로 멈춘다.
- PyAEDT `import_3d_cad`, `set_object_model_state`, `save_project`, EM setup calls, `ValidateDesign()`의 `False` return은 모두 즉시 예외다.
- GUI-visible AEDT는 이 흐름의 검증 경로가 아니다.

## Related Code Notes
- [[sdd/code/entry/generate_non_model_step.py]]
- [[sdd/code/entry/import_non_model_step_to_hfss.py]]
- [[sdd/code/entry/import_type2_step.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]
- [[sdd/code/src/peetsfea/aedt/wrappers.py]]
- [[sdd/code/src/peetsfea/aedt/protocols.py]]
- [[sdd/code/tests/backend_em/test_type2_step_import_smoke.py]]

## Related Plans / Diagrams
- [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]]
- [[sdd/plans/0.2.22-type2-toml-unification]]
- [[sdd/plans/0.2.22-type2-build123d-non-model-step]]
- [[sdd/plans/0.2.22-type2-pyaedt-step-import]]
- [[sdd/plans/0.2.22-type2-import-ledger-pipeline]]
- [[sdd/diagrams/type2-step-to-em-validate-flow]]
- [[sdd/structure/sdd-vault-layout]]
