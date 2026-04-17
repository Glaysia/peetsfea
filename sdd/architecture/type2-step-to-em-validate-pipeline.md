---
title: Type2 STEP to EM Validate Pipeline
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 00:20
tags:
  - type2
  - step-export
  - sdd
---

# Type2 STEP to EM Validate Pipeline

이 문서는 current type2 runtime을 import-only 단계와 setup-ready 단계로 분리한 현재 구현 경계를 설명한다.
세부 helper inventory는 graph edge로 연결하지 않고 plain text path로 유지한다.

## Current Split
- import-only owner:
  - entry: [[sdd/code/entry/import_type2_step.py]]
  - runtime: [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]
- setup-ready owner:
  - entry: [[sdd/code/entry/setup_type2_step.py]]
  - runtime: [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]
- notebook `view_type2_hfss_import.ipynb`는 setup-ready owner helper의 thin manual consumer다.

## Handoff
- input SSOT는 `examples/type2_fixed.toml`이다.
- build123d handoff artifact는:
  - `run/step/type2/type2_scene.step`
  - `run/step/type2/type2_step_ledger.json`
- retained policy key는 top-level `em_policy`다.
- import-only handoff artifact는 `run/aedt/type2_step_import/type2_imported_ledger.json`이다.
- imported ledger는 source paths, seed, imported ownership, imported object names만 보존한다.
- imported ledger는 mesh/boundary/ports/analysis summary를 canonical persisted owner로 갖지 않는다.

## Runtime Flow
1. export 단계가 single scene STEP와 retained step ledger를 만든다.
2. import-only runtime이 STEP import, ownership partition, style/material application, metadata-driven port-sheet reconstruction을 수행한다.
3. import-only runtime이 `.aedt`와 imported ledger를 저장한다.
4. setup-ready runtime은 같은 import core를 재사용한 뒤 아래를 순서대로 수행한다:
   - `AssignLengthOp`
   - radiation boundary
   - explicit lumped ports
   - source phase
   - analysis/report templates
   - `validate_pipeline()`
   - `ValidateDesign()`
   - final `.aedt` save

## Ownership
- radiation boundary의 canonical owner는 setup-ready runtime이다.
- explicit lumped port의 canonical owner도 setup-ready runtime이다.
- import-only runtime은 boundary/ports를 만들지 않는다.
- current explicit port contract는 reconstructed `tx_port_sheet` / `rx_port_sheet`를 사용한다.
- current edge ownership rule:
  - signal/start edge = `(v3, v0)`
  - reference/end edge = `(v1, v2)`
- current numeric port naming rule:
  - TX boundary/excitation = `1` / `1_T1`
  - RX boundary/excitation = `2` / `2_T1`

## Invariants / Fail-fast
- `import_3d_cad`, `save_project`, `release_desktop`, `AssignLengthOp`, `create_region`, `assign_radiation_boundary_to_faces`, `AssignLumpedPort`, source/analysis calls, `ValidateDesign()` false는 모두 즉시 raise다.
- attached-session path는 dirty design을 재사용하지 않고 fresh design으로 rehome해야 한다.
- current setup-ready baseline은 single-layer TX/RX exact contract만 지원한다.
- TX multilayer는 import-only에서는 허용되지만, setup-ready mesh/port exact contract generalization 전까지 fail-fast다.
- current import/runtime contract에서 `tx_port_sheet` / `rx_port_sheet`는 metadata-driven reconstructed sheet다. PCB/copper exact-name contract와 별도 ownership이다.

## Supporting Modules
- import body assembly: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py.md`
- post-import mesh/setup: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py.md`
- EM input assembly: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_input.py.md`
- explicit port assignment: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_port_assignment.py.md`

## Related
- Diagram: [[sdd/diagrams/type2-step-to-em-validate-flow]]
- Implementation plan: [[sdd/plans/0.2.22-type2-import-ledger-pipeline]]
