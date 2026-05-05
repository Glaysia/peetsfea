---
title: Type2 STEP to EM Validate Pipeline
created: 2026-04-17 @ 09:09
updated: 2026-05-03 @ 00:00
tags:
  - step-export
  - sdd
---

# Type2 STEP to EM Validate Pipeline

이 문서는 current type2 runtime split과 RxOnly setup-ready 계약을 설명한다.
TX 형상은 재설계 예정이므로 현 SDD에서 shape contract를 제거하고, `tx_region`만 future placement guide로 보존한다.

## Graph Owners
- Raw AEDT/PyAEDT wrapper and session access: [pyaedt-boundary](pyaedt-boundary.md)
- Import-only STEP-to-HFSS handoff: [type2-step-import-boundary](type2-step-import-boundary.md)
- Setup-ready and solve-ready HFSS handoff: [type2-em-setup-boundary](type2-em-setup-boundary.md)
- EM report variable contract: [type2-em-report-contract](type2-em-report-contract.md)

## Current Split
- sampled/build owner:
  - entry: `entry/sample.py`
  - entry: `entry/build.py`
- import-only owner:
  - entry: [import_type2_step.py](../code/entry/import_type2_step.py.md)
  - runtime: [type2_step_import_pipeline.py](../code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py.md)
  - graph owner: [type2-step-import-boundary](type2-step-import-boundary.md)
- setup-ready owner:
  - entry: [setup_type2_step.py](../code/entry/setup_type2_step.py.md)
  - runtime: [type2_step_setup_ready.py](../code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py.md)
  - graph owner: [type2-em-setup-boundary](type2-em-setup-boundary.md)
- active setup-ready owner는 RxOnly mode에서 RX port/report만 만든다.
- import-only helper는 geometry inspection / import-only surface다. active default build owner가 아니다.
- notebook `hfss_sampled.ipynb`는 sampled/build output artifact를 읽는 thin manual consumer다.
- notebook `view_step_files.ipynb`는 `VIEW_INDEX = -1`일 때 fixed example refresh path, `VIEW_INDEX >= 0`일 때 manifest `entries` order 기반 sampled STEP selection을 사용한다.

## Handoff
- source authoring SSOT는 `examples/type2_sweep.toml`이다.
- sampled build input SSOT는 `run/sampled/type2/<design_id>/sampled.toml`이다.
- build123d handoff artifact는:
  - `run/sampled/type2/<design_id>/type2_scene.step`
  - `run/sampled/type2/<design_id>/type2_step_ledger.json`
- retained policy key는 top-level `em_policy`다.
- import-only handoff artifact는 `run/sampled/type2/<design_id>/type2_imported_ledger.json`이다.
- imported ledger는 source paths, seed, imported ownership, imported object names만 보존한다.
- imported ledger는 mesh/boundary/ports/analysis summary를 canonical persisted owner로 갖지 않는다.
- `tx_region` is retained only as a non-modeled future TX placement guide.
- active EM report variables are defined by [type2-em-report-contract](type2-em-report-contract.md).

## Runtime Flow
1. sample 단계가 source TOML에서 frozen sampled TOML을 만들고, `make_step_on_sample=true`일 때만 same-worker scene STEP/retained step ledger까지 만든다.
2. sample 단계는 모든 sampled design이 끝난 뒤 manifest object를 기록한다.
   - manifest `entries` order is the notebook sampled-index SSOT
3. export-side non-model contract는 scene/export/import 계층이 소유한다.
   - `tx_region`은 future guide로 export될 수 있지만 EM setup 대상이 아니다.
   - RX non-model bodies may remain as import-visible context only when the RX path explicitly owns them.
4. build 단계가 retained step ledger를 재사용하거나 missing STEP을 same-worker에서 만든 뒤
   role-aware setup-ready runtime으로 `.aedt`와 imported ledger를 만든다.
5. import-only runtime이 STEP import, ownership partition, style/material application, metadata-driven port-sheet reconstruction을 수행한다.
6. setup-ready runtime은 같은 import core를 재사용한 뒤 RxOnly 후반부를 실행한다:
   - post-import mesh
   - radiation boundary
   - explicit RX lumped port
   - source phase
   - RX analysis/report templates
   - `validate_pipeline()`
   - `ValidateDesign()`
   - final `.aedt` save
7. notebook은 finished artifact만 읽고 sample/build/runtime을 다시 호출하지 않는다.

## Ownership
- radiation boundary의 canonical owner는 setup-ready runtime이다.
- explicit lumped port의 canonical owner도 setup-ready runtime이다.
- import-only runtime은 boundary/ports를 만들지 않는다.
- RxOnly explicit port contract는 RX reconstructed sheet를 사용한다.
  - RX boundary/excitation = `1` / `1_T1`
- `tx_region` guide의 canonical owner는 non-model scene/export 계층이다.
- guide bodies are never conductor mesh owners.
- current edge ownership rule:
  - signal/start edge = `(v3, v0)`
  - reference/end edge = `(v1, v2)`

## Invariants / Fail-fast
- `import_3d_cad`, `save_project`, `release_desktop`, `create_region`,
  `assign_radiation_boundary_to_faces`, `AssignLumpedPort` false는 모두 즉시 raise다.
- setup-ready full EM chain에서는 post-import mesh, source/analysis calls, `ValidateDesign()` false도 즉시 raise다.
- attached-session path는 dirty design을 재사용하지 않고 fresh design으로 rehome해야 한다.
- setup-ready mesh contract는 RX conductor-only exact set이다.
- TX guide bodies, RX context bodies, and reconstructed port sheets are not mesh targets.
- RxOnly mode must not create TX ports or TX output variables.
- generic `SOLID*` drift in modeled RX conductor import is an export-side contract failure.

## Supporting Boundaries
- Import body assembly and imported ledger: [type2-step-import-boundary](type2-step-import-boundary.md)
- Post-import mesh, EM input, port assignment, solve/report export: [type2-em-setup-boundary](type2-em-setup-boundary.md)
- Raw PyAEDT wrapper/protocol surface: [pyaedt-boundary](pyaedt-boundary.md)
- Report variables: [type2-em-report-contract](type2-em-report-contract.md)

## Related
- Diagram: [type2-step-to-em-validate-flow](../diagrams/type2-step-to-em-validate-flow.md)
- Implementation plan: [0.2.22-type2-import-ledger-pipeline](../plans/0.2.22-type2-import-ledger-pipeline.md)
