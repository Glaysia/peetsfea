---
title: type2_step_setup_ready.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 23:30
tags:
  - type2
  - hfss-import
  - em
---

# type2_step_setup_ready.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_setup_ready.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py.md`
- Related architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]
- Collaborators:
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_runtime_common.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_input.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_port_assignment.py]]

## 역할
- type2 full setup-ready runtime facade다.
- import-only handoff를 이어받아 post-import mesh, radiation boundary, explicit lumped ports, source phase, analysis/report templates, validation, final save를 orchestrate한다.

## 입력 / 출력
- 입력:
  - type2 STEP ledger path
  - output `.aedt` path
  - imported ledger path
  - optional attached `HfssSession`
- 출력:
  - in-memory `Type2SetupReadyResult`

## Canonical state
- explicit ports, shared EM setup call order, final save/release의 canonical owner다.
- import handoff가 남긴 imported ledger JSON을 그대로 write하고, setup-ready summary는 return value와 final `.aedt`에 남긴다.

## Invariants / fail-fast
- import-only ledger 이후 post-import `mesh` -> `boundary` -> lumped ports -> sources -> analysis/report -> repo validation -> `ValidateDesign()` -> save 순서를 유지한다.
- import core는 scene import까지만 소유하고, setup-ready가 mesh와 radiation boundary의 canonical owner다.
- current baseline은 RX `rx_copper_l0`를 고정으로 유지하면서, TX mesh target으로 `tx_copper_l0` 또는 `tx_copper_stack`를 지원한다.

## 직접 의존
- `peetsfea.backend.pyaedt.em_pipeline.contracts`
- `peetsfea.backend.pyaedt.em_pipeline.steps.analysis`
- `peetsfea.backend.pyaedt.em_pipeline.steps.sources`
- `peetsfea.backend.pyaedt.em_pipeline.validate`
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_input.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_port_assignment.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/entry/setup_type2_step.py]]
- `notebooks/view_type2_hfss_import.ipynb`

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]
- [[sdd/code/tests/type2/test_setup_type2_step_entry.py]]

## 변경 시 주의점
- `run_em_pipeline()`를 억지로 재사용해 boundary/mesh 중복 생성 경로를 만들지 않는다.
- import-only ledger를 setup-ready summary persisted owner로 승격하지 않는다.
- mesh/boundary owner를 다시 import 단계로 밀어 넣지 않는다.
