---
title: Type2 STEP to EM Validate Flow
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 00:20
tags:
  - type2
  - step-export
  - sdd
---

# Type2 STEP to EM Validate Flow

```mermaid
flowchart TD
    Type2Toml["examples/type2_fixed.toml"]
    Export["entry/generate_type2_step.py"]
    StepScene["run/step/type2/type2_scene.step"]
    StepLedger["run/step/type2/type2_step_ledger.json\n+ em_policy"]
    ImportEntry["entry/import_type2_step.py"]
    ImportCore["type2_step_import_core\nimport + partition + styling\n+ port-sheet reconstruction"]
    ImportLedger["run/aedt/type2_step_import/type2_imported_ledger.json"]
    ImportAedt["run/aedt/type2_step_import/type2_import.aedt"]
    SetupEntry["entry/setup_type2_step.py"]
    Mesh["type2_step_post_import_mesh\nLength1 on tx_copper_l0 + rx_copper_l0"]
    Boundary["build_boundary()\nabsolute-offset region\nexact 6 faces"]
    Ports["type2_step_port_assignment\n1/1_T1, 2/2_T1"]
    Adapter["type2_step_em_input\n-> EmPipelineInput"]
    Source["apply_sources_phase()"]
    Analysis["build_analysis() + build_post_templates()"]
    Validate["validate_pipeline() + ValidateDesign()"]
    SetupAedt["run/aedt/type2_step_setup_ready/type2_setup_ready.aedt"]
    Notebook["view_type2_hfss_import.ipynb"]

    Type2Toml --> Export
    Export --> StepScene
    Export --> StepLedger
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
- imported ledger는 import handoff artifact다. setup-ready summary를 JSON으로 누적하지 않는다.
- `tx_port_sheet` / `rx_port_sheet`는 STEP exact-name body가 아니라 metadata-driven reconstructed sheet다.
- radiation boundary와 explicit lumped port는 setup-ready runtime이 1회만 만든다.
