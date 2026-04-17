---
title: test_type2_step_import_pipeline.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 00:20
tags:
  - type2
  - hfss-import
---

# test_type2_step_import_pipeline.py

## Source
- Path: `tests/backend_em/test_type2_step_import_pipeline.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_step_import_pipeline.py.md`
- Tested source:
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]

## 역할
- type2 import-only runtime을 pure-Python fake HFSS seam으로 검증한다.
- import diff, ownership partition, styling, reconstructed port-sheet handoff, save/release contract를 검증한다.

## 입력 / 출력
- 입력:
  - test-local STEP placeholder
  - test-local STEP ledger JSON
  - fake HFSS/modeler/material/project seams
- 출력:
  - import-only `Type2ImportedLedger`
  - written imported ledger JSON
  - fake call history

## Canonical state
- fake call history와 written imported ledger JSON이 canonical assertion surface다.
- fake materials seam은 `add_material()` 성공 후에도 `material_keys` visibility가 지연되는 PyAEDT cache drift를 재현할 수 있어야 한다.
- shared fake mesh-payload helper는 setup-ready reuse를 위해 `tx_copper_l0`와 `tx_copper_stack` 둘 다 표현할 수 있어야 한다.

## Invariants / fail-fast
- import-only runtime은 conductor-only `AssignLengthOp`와 radiation boundary summary를 imported ledger handoff에 포함하고, explicit lumped port는 호출하지 않는다.
- missing optional port-sheet STEP body는 HFSS-side reconstruction으로 보정하되, modeled exact-name ownership은 PCB/copper에서만 평가한다.
- missing scene STEP, missing required field, duplicate object id, bad import diff, missing non-model member, placement violation, `import_3d_cad` false, `save_project` false는 모두 raise다.

## 직접 의존
- `pytest`
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 이 파일을 쓰는 곳
- Default pure-Python test suite.

## 관련 테스트
- setup-ready split coverage lives in [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]].

## 변경 시 주의점
- import-only assertions와 setup-ready assertions를 다시 한 파일에 섞지 않는다.
