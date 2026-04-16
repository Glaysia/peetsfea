# Type2 STEP to EM Validate Flow

이 다이어그램은 `examples/type2.toml`에서 type2 object-level STEP artifact와 imported ledger, 이후 EM validation까지 이어지는 flow를 보여준다. Import+Ledger 구현 계획은 [[sdd/plans/0.2.22-type2-import-ledger-pipeline]], 상위 계획은 [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]], TOML 단일화 계획은 [[sdd/plans/0.2.22-type2-toml-unification]], 아키텍처 설명은 [[sdd/architecture/type2-step-to-em-validate-pipeline]]다.

```mermaid
flowchart TD
    Type2Toml["examples/type2.toml"]
    Registry["type2 object registry\nnon_model_objects + modeled_objects"]
    Export["object-level build123d STEP export"]
    StepLedger["STEP artifact ledger"]
    ImportRuntime["entry/import_type2_step.py\n+ type2_step_import_pipeline"]
    Import["headless HFSS import_3d_cad\nset model state"]
    ImportLedger["type2_imported_ledger.json"]
    Adapter["type2 ledger -> EmPipelineInput adapter"]
    EM["run_em_pipeline()"]
    RepoValidate["validate_pipeline()"]
    AedtValidate["Hfss.odesign.ValidateDesign()"]
    Result["validation report / AEDT design state"]

    Type2Toml --> Registry
    Registry --> Export
    Export --> StepLedger
    StepLedger --> ImportRuntime
    ImportRuntime --> Import
    Import --> ImportLedger
    ImportLedger --> Adapter
    Adapter --> EM
    EM --> RepoValidate
    RepoValidate --> AedtValidate
    AedtValidate --> Result

    Import -. false return raises .-> ImportLedger
    EM -. false return raises .-> RepoValidate
    AedtValidate -. false return raises .-> Result
```

## Notes
- `examples/type2.toml` is the single planned public authoring input.
- STEP artifact granularity is object-level, not one monolithic compound for the full type2 scene.
- The STEP ledger and imported ledger are the canonical role/coordinate handoff; AEDT geometry reverse-calculation is not part of the flow.
- Import+Ledger is implemented by [[sdd/code/entry/import_type2_step.py]] and [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]].
- Validation includes both repository EM readiness and AEDT design validation.
- GUI validation is intentionally outside this planned path.
