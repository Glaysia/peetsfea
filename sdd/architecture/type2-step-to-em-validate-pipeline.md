---
title: Type2 STEP to EM Validate Pipeline
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 19:55
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
- 현재 구현 범위는 import+ledger까지이고, future active target은 single scene STEP + runtime-owned post-import mesh + type2 policy-owned radiation boundary + `EmPipelineInput` + explicit port/analysis + `ValidateDesign()`까지의 runtime-owned setup-ready state다. notebook은 그 상태를 호출/확인하는 thin consumer다.
- 이 문서의 radiation-boundary handoff는 planned contract다. import runtime이 region 생성, exact 6-face radiation assignment, boundary metadata persistence를 실제로 수행하기 전까지는 구현 완료로 간주하지 않는다.

## Boundary
- 입력 SSOT는 `examples/type2_fixed.toml`이다.
- `type2_fixed.toml`은 non-model guide objects와 modeled objects를 같은 object registry 안에서 표현한다.
- future type2 boundary-policy ownership도 `examples/type2_fixed.toml`에 두되 public TOML field path는 아직 고정하지 않는다. retained STEP ledger persisted field는 top-level `em_policy`로 고정한다.
- geometry authoring은 build123d가 담당하고, Ansys/HFSS는 headless PyAEDT import 이후 EM setup과 validation을 담당한다.
- canonical single scene STEP `run/step/type2/type2_scene.step`와 retained metadata ledger `run/step/type2/type2_step_ledger.json`이 build123d와 PyAEDT 사이의 경계다.
- future modeled single-coil exact-name STEP contract includes one separate port-sheet body per coil: `tx_port_sheet`, `rx_port_sheet`.
- the current type2 single-coil scene therefore has exactly two such sheet bodies total: one TX and one RX.
- the canonical port-sheet reference geometry connects the two terminal stubs of a coil by bridging one deterministic bottom-square diagonal from each stub in their shared bottom-face plane.
- planned radiation-boundary policy owner는 type2 input/STEP ledger다. canonical persisted field는 `type2_step_ledger.em_policy`이며 import runtime은 policy consumer일 뿐 margin, region semantics, radiation face count를 자체 추론하거나 fallback으로 보정하지 않는다.
- planned imported ledger owner는 realized boundary metadata persistence다. import runtime이 region 생성과 radiation assignment를 마치면 imported ledger top-level metadata에 requested `em_policy`와 realized boundary summary를 함께 남기는 방향을 계약으로 둔다.
- 현재 importer implementation이 `import_time_policy`를 기대하는 drift가 있고 `notebooks/view_type2_hfss_import.ipynb` 실패는 그 mismatch를 드러낸다. canonical docs는 `em_policy` 기준이며 runtime fix는 후속 코드 작업이다.
- `EmPipelineInput`이 imported AEDT object ledger와 기존 EM pipeline 사이의 경계다.
- 출력은 imported AEDT object ledger, setup-ready `.aedt`, EM pipeline result, repo validation report, AEDT `ValidateDesign()` 결과다.

## Planned Radiation-Boundary Handoff
1. Type2 authoring input이 boundary policy를 명시한다.
2. STEP export 단계가 그 policy를 retained STEP ledger top-level `em_policy`에 lossless로 보존한다.
3. Headless import runtime이 `type2_step_ledger.em_policy`를 읽고 imported scene 바깥에 absolute-offset region 하나를 생성한다.
4. Runtime은 생성된 region의 face set을 읽고 exact 6-face contract를 검증한 뒤 radiation boundary를 6개 face 모두에 적용한다.
5. Runtime은 imported ledger에 boundary metadata를 저장한다. 최소 범위는 requested `em_policy`/policy source, created region name, resolved face ids or equivalent face summary, radiation assignment summary다.
6. 이후 `EmPipelineInput`과 EM validation은 runtime-owned setup-ready state를 전제로 이어진다.

- 이 handoff는 future/planned 상태다. 아직 구현되지 않은 동안에는 notebook이나 downstream pipeline이 boundary policy를 대신 소유하거나 boundary metadata를 임의로 합성하면 안 된다.

## Flow
1. `examples/type2_fixed.toml`이 object id, role, material, model_state, canonical coordinates를 확정한다.
2. Type2 parser가 `[[non_model_objects]]`와 `[[modeled_objects]]`를 같은 registry model로 읽는다.
3. Build123d export 단계가 single scene STEP 하나를 만들고 metadata ledger에 object-level `object_id`, `role`, `material`, `model_state`, canonical coordinates를 기록한다.
4. single-coil modeled body sets are planned to include PCB, copper, and one separate port-sheet body per coil. the sheet bodies are top-level STEP children and are not fused into copper or cut from PCB.
5. `notebooks/view_step_files.ipynb`는 `type2_scene.step` fixed path만 refresh/show하고 artifact index selection을 하지 않는다.
6. Headless HFSS import 단계가 single scene STEP를 import하고, import 전후 `modeler.object_names` diff를 검증해 `imported_object_names`를 ledger에 추가한다.
7. 같은 runtime이 imported ownership을 partition하고 imported ledger JSON을 확정한다.
8. 같은 import runtime이 `MeshSetup.AssignLengthOp(...)`를 적용한다. current single-coil exact contract는 `Length1`, objects `["tx_copper_l0", "rx_copper_l0"]`, `RefineInside=False`, `Enabled=True`, `RestrictElem=False`, `NumMaxElem="1000"`, `RestrictLength=True`, `MaxLength="5mm"`다.
9. 같은 import runtime이 STEP ledger top-level `em_policy`를 읽어 absolute-offset region 하나를 생성하고, exact 6-face contract를 검증한 뒤 radiation assignment를 수행하는 방향으로 확장된다.
10. 같은 runtime이 requested `em_policy`, created region identity, realized face summary, radiation assignment summary를 imported ledger JSON top-level metadata에 기록하는 방향으로 확장된다.
11. Post-import adapter가 ledger role을 읽어 `EmPipelineInput.ready_objects`, `ports`, `context`, `endpoints`를 조립한다.
12. later port adapter work will consume imported `tx_port_sheet` / `rx_port_sheet` ownership as reference surfaces for explicit lumped-port creation; this is planned, not current implementation.
13. `run_em_pipeline()`가 grouping, series/subtract metadata, explicit ports, source phase, analysis setup, post template creation을 수행한다. radiation boundary는 type2 import path에서 먼저 적용된 setup-ready state를 전제로 문서화한다.
14. `validate_pipeline()`가 repo-level TX/RX conductor readiness를 검사하고, AEDT `ValidateDesign()`가 design-level validation을 수행한다.
15. `notebooks/view_type2_hfss_import.ipynb`는 runtime이 만든 state를 수동으로 호출/확인한다. setup-ready ownership은 notebook이 아니라 runtime/entry/pipeline에 있다.

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
- future boundary 단계에서도 boundary policy owner가 비어 있거나 STEP ledger top-level `em_policy`가 누락되면 즉시 실패한다.
- future boundary 단계에서도 TOML-derived policy와 STEP ledger persisted policy가 불일치하면 즉시 실패한다.
- future boundary 단계에서도 `radiation_margin_mm` 누락/invalid, `create_region` false, created region count mismatch, `get_object_faces` false, non-6-face region, face summary persistence failure, radiation assignment false는 모두 즉시 실패한다.
- boundary 단계에서는 fallback margin, alternate region shape, partial-face assignment, notebook-side repair를 허용하지 않는다.

## Intentionally Unresolved
- EM mapping role taxonomy
- multi-object / multi-coil composition
- solve execution automation policy

## Invariants
- 하나의 type2 object id는 하나의 canonical object registry owner를 가진다.
- imported object role과 coordinates는 `type2_fixed.toml`에서 파생된 metadata ledger에서 읽는다. AEDT 내부 geometry에서 역산하지 않는다.
- imported object diff가 비어 있거나 중복 이름을 만들면 즉시 실패한다.
- current single-coil setup-ready baseline은 import 직후 runtime이 exact LengthOp payload를 적용하는 post-import mesh 단계를 포함한다.
- type2 policy-owned radiation boundary는 type2 input에서 정의되고 STEP ledger top-level `em_policy`를 통해 import runtime으로 전달된다. runtime은 그 policy를 소비할 뿐 새 값을 추론하지 않는다.
- planned setup-ready path에서는 region이 정확히 하나여야 하고 radiation assignment 대상은 정확히 6 face여야 한다.
- imported ledger는 boundary summary를 top-level metadata로 보존하는 방향을 유지한다. boundary metadata omission은 silent degradation이 아니라 failure여야 한다.
- future single-coil modeled exact-name contract keeps port-sheet bodies separate from copper/PCB styling ownership.
- `EmPipelineInput`은 TX/RX conductor와 explicit port 계약을 만족해야 하며, 그렇지 않으면 `run_em_pipeline()` 또는 `validate_pipeline()`가 fail-fast로 멈춘다.
- PyAEDT `import_3d_cad`, `set_object_model_state`, `AssignLengthOp`, `create_region`, `get_object_faces`, `assign_radiation_boundary_to_faces`, `save_project`, EM setup calls, `ValidateDesign()`의 `False` return은 모두 즉시 예외다.
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
