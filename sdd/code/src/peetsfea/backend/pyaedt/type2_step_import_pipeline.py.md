---
title: type2_step_import_pipeline.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - hfss-import
  - aedt
---

# type2_step_import_pipeline.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py.md`
- Primary plan: [[sdd/plans/0.2.22-type2-import-ledger-pipeline]]
- Primary architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- type2 import-only facade다.
- headless HFSS lifecycle, attached-session fresh-design rehome, final import-only save/release를 소유한다.
- import body assembly는 `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py.md` contract로 위임한다.

## 입력 / 출력
- 입력:
  - `run/step/type2/type2_step_ledger.json`
  - optional attached `HfssSession`
- 출력:
  - `run/aedt/type2_step_import/type2_import.aedt`
  - `run/aedt/type2_step_import/type2_imported_ledger.json`
  - import-only `Type2ImportedLedger`

## Canonical state
- module-level mutable state는 없다.
- imported ledger schema의 public owner surface다.
- current imported ledger는 source paths, seed, imported ownership, imported object names만 보존한다.

## Invariants / fail-fast
- import-only path는 scene import, ownership partition, styling, port-sheet reconstruction, imported ledger write까지만 수행한다.
- `AssignLengthOp`, `build_boundary`, `AssignLumpedPort`, source phase, analysis, `ValidateDesign()`는 import-only 단계에서 호출하지 않는다.
- attached-session path는 dirty design object set이 비어 있지 않으면 fresh design으로 rehome해야 한다.
- `import_3d_cad`, `save_project`, `release_desktop` false는 즉시 raise다.

## 직접 의존
- `peetsfea.aedt.failfast`
- `peetsfea.aedt.protocols`
- Direct collaborator notes:
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_runtime_common.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/entry/import_type2_step.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]
- entry-level smoke coverage is also exercised by `sdd/code/tests/type2/test_import_type2_step_entry.py.md`.

## 변경 시 주의점
- import-only ledger schema를 setup-ready summary로 다시 확장하지 않는다.
- mesh/boundary/ports ownership을 이 facade로 되돌리지 않는다.
