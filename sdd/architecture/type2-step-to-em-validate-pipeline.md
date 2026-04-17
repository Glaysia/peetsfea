---
title: Type2 STEP to EM Validate Pipeline
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - type2
  - step-export
  - sdd
---

# Type2 STEP to EM Validate Pipeline

이 문서는 `examples/type2_fixed.toml`에서 canonical single scene STEP와 retained metadata ledger를 거쳐 setup-ready HFSS state와 EM validation까지 이어지는 ownership handoff를 설명한다. 상위 계획은 [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]], single scene/setup-ready 방향은 [[sdd/plans/0.2.22-type2-single-step-setup-ready-pipeline]], type2 TOML 단일화 계획은 [[sdd/plans/0.2.22-type2-toml-unification]]이다.

## Implementation Status
- Import+Ledger 단계는 [[sdd/plans/0.2.22-type2-import-ledger-pipeline]]에서 구현됐다.
- Runtime entry는 [[sdd/code/entry/import_type2_step.py]]이고 core runtime은 [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]다.
- 현재 구현 범위는 import+ledger까지이고, future active target은 single scene STEP + `EmPipelineInput` + explicit port/boundary/analysis + `ValidateDesign()`까지의 runtime-owned setup-ready state다. notebook은 그 상태를 호출/확인하는 thin consumer다.

## Boundary
- 입력 SSOT는 `examples/type2_fixed.toml`이다.
- `type2_fixed.toml`은 non-model guide objects와 modeled objects를 같은 object registry 안에서 표현한다.
- geometry authoring은 build123d가 담당하고, Ansys/HFSS는 headless PyAEDT import 이후 EM setup과 validation을 담당한다.
- canonical single scene STEP `run/step/type2/type2_scene.step`와 retained metadata ledger `run/step/type2/type2_step_ledger.json`이 build123d와 PyAEDT 사이의 경계다.
- `EmPipelineInput`이 imported AEDT object ledger와 기존 EM pipeline 사이의 경계다.
- 출력은 imported AEDT object ledger, setup-ready `.aedt`, EM pipeline result, repo validation report, AEDT `ValidateDesign()` 결과다.

## Flow
1. `examples/type2_fixed.toml`이 object id, role, material, model_state, canonical coordinates를 확정한다.
2. Type2 parser가 `[[non_model_objects]]`와 `[[modeled_objects]]`를 같은 registry model로 읽는다.
3. Build123d export 단계가 single scene STEP 하나를 만들고 metadata ledger에 object-level `object_id`, `role`, `material`, `model_state`, canonical coordinates를 기록한다.
4. `notebooks/view_step_files.ipynb`는 `type2_scene.step` fixed path만 refresh/show하고 artifact index selection을 하지 않는다.
5. Headless HFSS import 단계가 single scene STEP를 import하고, import 전후 `modeler.object_names` diff를 검증해 `imported_object_names`를 ledger에 추가한다.
6. Import+Ledger runtime이 imported ownership을 partition하고 imported ledger JSON을 쓴다.
7. Post-import adapter가 ledger role을 읽어 `EmPipelineInput.ready_objects`, `ports`, `context`, `endpoints`를 조립한다.
8. `run_em_pipeline()`가 grouping, series/subtract metadata, radiation boundary, explicit ports, source phase, analysis setup, post template creation을 수행한다.
9. `validate_pipeline()`가 repo-level TX/RX conductor readiness를 검사하고, AEDT `ValidateDesign()`가 design-level validation을 수행한다.
10. `notebooks/view_type2_hfss_import.ipynb`는 runtime이 만든 state를 수동으로 호출/확인한다. setup-ready ownership은 notebook이 아니라 runtime/entry/pipeline에 있다.

## Type2 TOML Object Bridge
- `type2_fixed.toml`의 `[[non_model_objects]]`는 scene/envelope guide object의 canonical source다.
- `type2_fixed.toml`의 `[[modeled_objects]]`는 generated STEP modeled object의 canonical source다.
- 현재 single-coil prototype은 `tx_single_coil`, `rx_single_coil`을 같은 export engine 위에서 role-specific profile로 생성한다. example의 첫 modeled object는 `role = "tx_single_coil"`인 `tx_rect_void` TX coil이다.
- `tx_rect_void` geometry authoring code may be reused internally, but the public input ownership is `type2_fixed.toml`.
- Removed split TOML inputs are not type2 public SSOT.

## Future Layering Direction
1. `type2_fixed.toml` modeled object registry
2. generalized single-coil parser/resolver contract
3. generalized single-coil geometry/export engine
4. role/profile adapters
   - `tx_single_coil`
   - `rx_single_coil`
5. role-specific placement contracts
6. import/ledger/EM adapter handoff

- current engine commonization is partial and naming/public surface are still TX-biased.
- generalized single-coil engine is prerequisite work before TX multilayer geometry is implemented.
- first multilayer milestone applies to `tx_single_coil` only; `rx_single_coil` remains single-layer-only even after engine generalization.
- future canonical stub rule is derived `layer_gap_mm * 0.8`, not public explicit `terminal_stub_length_mm`.
- current `examples/type2_fixed.toml` may intentionally lead the implementation; notebook refresh failure from `tx layer_count = 2` is an implementation-gap symptom, not a user/operator fault.

## Prototype Matching Rules
- tx-only convenience export path는 정확히 하나의 `role = "tx_single_coil"` modeled object를 요구하고, full ledger path는 TX/RX single-coil entries를 함께 가질 수 있다.
- setup-ready path의 imported names는 single scene STEP import diff에서 나오며, role/ownership partition은 metadata ledger를 기준으로 수행한다.
- object role, coordinates, terminal meaning은 `type2_fixed.toml`-derived metadata ledger에서 읽고, imported object names만 import 결과에서 읽는다.
- AEDT live geometry를 다시 측정해 role, coordinates, terminal semantics를 역산하지 않는다.
- imported ownership partition과 `EmPipelineInput` 조립은 pipeline team 경계이며 geometry authoring 단계와 분리한다.

## Fail-fast
- `type2_fixed.toml`에 unsupported modeled object role이 있으면 즉시 실패한다.
- tx-only convenience export path에서 `tx_single_coil` modeled object count가 1이 아니면 즉시 실패한다.
- metadata `step_path`와 실제 import input이 다르면 즉시 실패한다.
- import diff가 비어 있으면 즉시 실패한다.
- import diff에 duplicate imported names가 있으면 즉시 실패한다.

## Intentionally Unresolved
- EM mapping role taxonomy
- multi-object / multi-coil composition
- solve execution automation policy

## Invariants
- 하나의 type2 object id는 하나의 canonical object registry owner를 가진다.
- imported object role과 coordinates는 `type2_fixed.toml`에서 파생된 metadata ledger에서 읽는다. AEDT 내부 geometry에서 역산하지 않는다.
- imported object diff가 비어 있거나 중복 이름을 만들면 즉시 실패한다.
- `EmPipelineInput`은 TX/RX conductor와 explicit port 계약을 만족해야 하며, 그렇지 않으면 `run_em_pipeline()` 또는 `validate_pipeline()`가 fail-fast로 멈춘다.
- PyAEDT `import_3d_cad`, `set_object_model_state`, `save_project`, EM setup calls, `ValidateDesign()`의 `False` return은 모두 즉시 예외다.
- GUI-visible AEDT는 이 흐름의 검증 경로가 아니다.
- `notebooks/view_step_files.ipynb`는 future contract에서 fixed single STEP viewer이며 index selection을 하지 않는다.
- `notebooks/view_type2_hfss_import.ipynb`는 future contract에서 auto-solve owner가 아니라 runtime-owned setup-ready/manual-solve-ready state를 확인하는 thin manual notebook이다.

## TODO
- [ ] prototype 설명에서 TX-only로 읽히는 문장을 current TX/RX single-coil prototype reality와 맞추는 정리 작업을 계속 기록한다.
- [ ] type2 public single-coil interface를 TX/RX 공통 surface로 정리하고 tx-only convenience surface를 축소하는 후속 작업을 기록한다.
- [ ] engine commonization은 진행됐지만 naming/public surface는 아직 TX 편향이라는 구조 부채를 architecture level TODO로 유지한다.

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
- [[sdd/plans/0.2.22-type2-single-step-setup-ready-pipeline]]
- [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]]
- [[sdd/plans/0.2.22-type2-toml-unification]]
- [[sdd/plans/0.2.22-type2-build123d-non-model-step]]
- [[sdd/plans/0.2.22-type2-pyaedt-step-import]]
- [[sdd/plans/0.2.22-type2-import-ledger-pipeline]]
- [[sdd/plans/0.2.22-type2-multilayer-tx-generic-single-coil]]
- [[sdd/diagrams/type2-step-to-em-validate-flow]]
- [[sdd/structure/sdd-vault-layout]]
