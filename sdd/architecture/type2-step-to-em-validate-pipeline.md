---
title: Type2 STEP to EM Validate Pipeline
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - step-export
  - sdd
---

# Type2 STEP to EM Validate Pipeline

이 문서는 current type2 runtime split을 설명하고, 0.2.23 underlay 관련 문서-first 계약도 함께 고정한다.
세부 helper inventory는 graph edge로 연결하지 않고 plain text path로 유지한다.

## Current Split
- sampled/build owner:
  - entry: `entry/sample.py`
  - entry: `entry/build.py`
- import-only owner:
  - entry: [[sdd/code/entry/import_type2_step.py]]
  - runtime: [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]
- setup-ready owner:
  - entry: [[sdd/code/entry/setup_type2_step.py]]
  - runtime: [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]
- notebook `hfss_sampled.ipynb`는 sampled/build output artifact를 읽는 thin manual consumer다.

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
- 0.2.23 underlay document contract:
  - `underlay_repeat_count`는 TX/RX shared field이며 canonical encoding은 `[true, 0, 8, 5]`다.
  - `underlay_gap_mm`는 TX-only field이며 canonical encoding은 `[false, 1.0, 10.0, 4]`다.
  - TX underlay footprint는 `tx_region` full `XY` bounds다.
  - RX underlay footprint는 `rx_region_max` full `YZ` bounds다.
  - TX exact names는 `tx_underlay_*`, RX exact names는 `under_rx_*`다.
  - new underlay exact object/body names는 feature-local rule로 `<= 32` chars여야 한다.

## Runtime Flow
1. sample 단계가 source TOML에서 frozen sampled TOML과 per-design manifest entry를 만든다.
2. sample 단계가 같은 manifest entries를 다시 읽어 single scene STEP와 retained step ledger를 만든다.
3. export-side underlay contract는 scene/export/import 계층이 소유한다.
   - TX는 `tx_region` full footprint + TX-only `underlay_gap_mm`
   - RX는 `rx_region_max` `-X` boundary anchor + full region footprint
4. build 단계가 retained step ledger를 읽어 setup-ready runtime으로 `.aedt`와 imported ledger를 만든다.
5. import-only runtime이 STEP import, ownership partition, style/material application, metadata-driven port-sheet reconstruction을 수행한다.
6. setup-ready runtime은 같은 import core를 재사용한 뒤 아래를 순서대로 수행한다:
   - `AssignLengthOp`
   - radiation boundary
   - explicit lumped ports
   - source phase
   - analysis/report templates
   - `validate_pipeline()`
   - `ValidateDesign()`
   - final `.aedt` save
7. notebook은 finished artifact만 읽고 sample/build/runtime을 다시 호출하지 않는다.

## Ownership
- radiation boundary의 canonical owner는 setup-ready runtime이다.
- explicit lumped port의 canonical owner도 setup-ready runtime이다.
- import-only runtime은 boundary/ports를 만들지 않는다.
- current explicit port contract는 reconstructed `tx_port_sheet` / `rx_port_sheet`를 사용한다.
- underlay geometry/footprint/gap contract의 canonical owner는 type2 scene/export/import 계층이다.
- underlay bodies는 imported exact-name solids지만 conductor mesh owner는 아니다.
- RX underlay absolute stack는 `rx_region_max` `-X` boundary에 anchor하고, coil-facing material은 ferrite다.
- current edge ownership rule:
  - signal/start edge = `(v3, v0)`
  - reference/end edge = `(v1, v2)`
- current numeric port naming rule:
  - TX boundary/excitation = `1` / `1_T1`
  - RX boundary/excitation = `2` / `2_T1`

## Invariants / Fail-fast
- `import_3d_cad`, `save_project`, `release_desktop`, `AssignLengthOp`, `create_region`, `assign_radiation_boundary_to_faces`, `AssignLumpedPort`, source/analysis calls, `ValidateDesign()` false는 모두 즉시 raise다.
- attached-session path는 dirty design을 재사용하지 않고 fresh design으로 rehome해야 한다.
- setup-ready mesh contract는 conductor-only exact set이다: `tx_copper_l0 | tx_copper_stack` + `rx_copper_l0`.
- TX/RX underlay exact-name bodies와 reconstructed port sheets는 mesh 대상에 들어가지 않는다.
- current import/runtime contract에서 `tx_port_sheet` / `rx_port_sheet`는 metadata-driven reconstructed sheet다. PCB/copper exact-name contract와 별도 ownership이다.

## Supporting Modules
- import body assembly: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py.md`
- post-import mesh/setup: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py.md`
- EM input assembly: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_input.py.md`
- explicit port assignment: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_port_assignment.py.md`

## Related
- Diagram: [[sdd/diagrams/type2-step-to-em-validate-flow]]
- Implementation plan: [[sdd/plans/0.2.22-type2-import-ledger-pipeline]]
