---
title: Type2 STEP to EM Validate Flow
created: 2026-04-17 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - step-export
  - sdd
---

# Type2 STEP to EM Validate Flow

```mermaid
flowchart TD
    Type2Toml["examples/type2_sweep.toml"]
    SampleEntry["entry/sample.py"]
    SampledToml["run/sampled/type2/<design_id>/sampled.toml"]
    BuildEntry["entry/build.py"]
    Export["entry/generate_type2_step.py"]
    StepScene["run/sampled/type2/<design_id>/type2_scene.step"]
    StepLedger["run/sampled/type2/<design_id>/type2_step_ledger.json\n+ em_policy"]
    ImportEntry["entry/import_type2_step.py"]
    ImportCore["type2_step_import_core\nimport + partition + styling\n+ RX port-sheet reconstruction"]
    ImportLedger["run/sampled/type2/<design_id>/type2_imported_ledger.json"]
    ImportAedt["run/sampled/type2/<design_id>/<design_id>.aedt"]
    SetupEntry["entry/setup_type2_step.py"]
    Mesh["type2_step_post_import_mesh\nLength1 on RX conductor-only target"]
    Boundary["build_boundary()\nabsolute-offset region\nexact 6 faces"]
    Ports["type2_step_port_assignment\nRxOnly 1/1_T1"]
    Adapter["type2_step_em_input\n-> EmPipelineInput"]
    Source["apply_sources_phase()"]
    Analysis["build_analysis() + RX report templates"]
    Validate["validate_pipeline() + ValidateDesign()"]
    SetupAedt["run/aedt/type2_step_setup_ready/type2_setup_ready.aedt"]
    Notebook["hfss_sampled.ipynb"]

    Type2Toml --> SampleEntry
    SampleEntry --> SampledToml
    SampleEntry -->|MAKE_STEP_ON_SAMPLE=true| Export
    Export --> StepScene
    Export --> StepLedger
    SampledToml --> BuildEntry
    StepLedger --> BuildEntry
    BuildEntry -->|missing-only| Export
    StepScene --> ImportEntry
    StepLedger --> ImportEntry
    ImportEntry --> ImportCore
    ImportCore --> ImportLedger
    ImportCore --> ImportAedt

    StepScene --> SetupEntry
    StepLedger --> SetupEntry
    SetupEntry --> ImportCore
    ImportCore --> Mesh
    Mesh --> Boundary
    Boundary --> Ports
    Ports --> Adapter
    Adapter --> Source
    Source --> Analysis
    Analysis --> Validate
    Validate --> SetupAedt
    SetupAedt --> Notebook
```

## Notes
- import-only와 setup-ready는 서로 다른 owner surface다.
- `entry/sample.py`의 STEP export는 optional이고, `entry/build.py`가 missing STEP을 same-worker에서 보완할 수 있다.
- imported ledger는 import handoff artifact다. setup-ready summary를 JSON으로 누적하지 않는다.
- RX port sheet는 STEP exact-name body가 아니라 metadata-driven reconstructed sheet다.
- RxOnly mode creates one RX port and RX report variables only.
- Active report variables are defined by [type2-em-report-contract](../architecture/type2-em-report-contract.md).
- TX geometry SDD is intentionally removed; `tx_region` may remain as a non-modeled future guide only.
- import에서 RX modeled body가 generic `SOLID*`로 보이면 export contract failure로 본다.
- radiation boundary와 explicit lumped port는 setup-ready runtime이 1회만 만든다.
- RxOnly setup-ready는 source phase, RX analysis/report, `validate_pipeline()`,
  `ValidateDesign()`, final save까지 full EM chain을 같은 순서로 수행한다.
- mesh owner는 계속 RX conductor-only다. `tx_region` guide와 reconstructed port-sheet는 mesh target set에 들어가지 않는다.

## Handoff
- Owning architecture: [type2-step-to-em-validate-pipeline](../architecture/type2-step-to-em-validate-pipeline.md)
- Primary plan: [0.2.22-type2-import-ledger-pipeline](../plans/0.2.22-type2-import-ledger-pipeline.md)
