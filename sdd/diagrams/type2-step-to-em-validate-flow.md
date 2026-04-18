---
title: Type2 STEP to EM Validate Flow
created: 2026-04-17 @ 09:09
updated: 2026-04-19 @ 11:05
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
    ImportCore["type2_step_import_core\nimport + partition + styling\n+ port-sheet reconstruction"]
    ImportLedger["run/sampled/type2/<design_id>/type2_imported_ledger.json"]
    ImportAedt["run/sampled/type2/<design_id>/<design_id>.aedt"]
    SetupEntry["entry/setup_type2_step.py"]
    Mesh["type2_step_post_import_mesh\nLength1 on tx_copper_l0|tx_copper_stack + rx_copper_l0"]
    Boundary["build_boundary()\nabsolute-offset region\nexact 6 faces"]
    Ports["type2_step_port_assignment\n1/1_T1, 2/2_T1"]
    Adapter["type2_step_em_input\n-> EmPipelineInput"]
    Source["apply_sources_phase()"]
    Analysis["build_analysis() + build_post_templates()"]
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
- `tx_port_sheet` / `rx_port_sheet`는 STEP exact-name body가 아니라 metadata-driven reconstructed sheet다.
- radiation boundary와 explicit lumped port는 setup-ready runtime이 1회만 만든다.
- 0.2.23 document contract에서 underlay footprint source는 coil bounds가 아니라 owner region full bounds다.
- TX underlay는 `tx_region` full `XY` footprint + TX-only `underlay_gap_mm`, RX underlay는 `rx_region_max` full `YZ` footprint + `-X` boundary anchor를 쓴다.
- underlay exact names는 TX `tx_underlay_*`, RX `under_rx_*`이며, underlay exact object/body names는 feature-local rule로 `<= 32` chars다.
- mesh owner는 계속 conductor-only다. underlay bodies는 imported participant지만 mesh target set에는 들어가지 않는다.
