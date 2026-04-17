---
title: Sample Build Flow
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - type1
  - sdd
---

# Sample Build Flow

이 구조도는 현재 샘플링에서 build replay로 넘어가는 흐름의 SDD 요약이다. 서술형 설명은 [[sdd/architecture/current-pipeline-sdd-view]], 자세한 분석은 [[docs/current-pipeline]]를 본다.

```mermaid
flowchart TD
    Source["run/type1.toml"]
    Loader["[[sdd/code/src/peetsfea/spec/loader.py]]"]
    Sample["[[sdd/code/entry/sample.py]]"]
    Manifest["run/toml/.../manifest.json"]
    Build["entry/build.py"]
    Geometry["src/peetsfea/backend/pyaedt/geometry/build.py"]
    EM["src/peetsfea/backend/pyaedt/em_pipeline/runner.py"]
    Tests["[[sdd/code/tests/spec_resolver/test_sampling_registry.py]]"]

    Source --> Loader
    Loader --> Sample
    Sample --> Manifest
    Manifest --> Build
    Build --> Geometry
    Geometry --> EM
    Tests -. guards sampling contracts .-> Sample
```

## Notes
- loader 단계는 fallback 없이 parse/shape 오류를 raise한다.
- sample 단계는 batch profile, seed selection, manifest write를 묶는다.
- 테스트 노트는 sampling registry와 preflight fail-fast 계약을 대표 예시로 가리킨다.

## Type2 STEP Import Smoke Flow

이 흐름은 `examples/type2_fixed.toml`에서 생성된 type2 STEP artifact를 HFSS로 가져오는 opt-in smoke path다. `entry/build.py` runtime replay나 EM pipeline에는 아직 연결하지 않는다.

```mermaid
flowchart TD
    Type2Toml["examples/type2_fixed.toml\nSSOT"]
    StepExport["entry/generate_type2_step.py"]
    StepArtifact["run/step/type2/objects/*.step"]
    SmokeImport["entry/import_tx_rect_void_step_to_hfss.py"]
    HeadlessHfss["headless HFSS via PyAEDT"]
    ImportCad["Modeler3D.import_3d_cad()"]
    NonModelState["set_object_model_state(..., False)"]
    SmokeAedt["run/aedt/type2_step_import_smoke/*.aedt"]
    RuntimeBuild["entry/build.py runtime replay"]
    EmRuntime["EM pipeline"]

    Type2Toml --> StepExport
    StepExport --> StepArtifact
    StepArtifact --> SmokeImport
    SmokeImport --> HeadlessHfss
    HeadlessHfss --> ImportCad
    ImportCad --> NonModelState
    NonModelState --> SmokeAedt
    SmokeImport -. not wired .-> RuntimeBuild
    SmokeImport -. not wired .-> EmRuntime
```

## Related notes
- [[sdd/plans/0.2.22-type2-pyaedt-step-import]]
- [[sdd/code/entry/import_non_model_step_to_hfss.py]]
