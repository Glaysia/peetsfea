---
title: type2_step_import_core.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - hfss-import
---

# type2_step_import_core.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_core.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py.md`
- Related architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]
- Collaborators:
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py]]

## 역할
- type2 STEP import core orchestration을 소유한다.
- scene import, ownership partition, scene-global underlay material preparation, style/material application, metadata-driven port-sheet reconstruction, imported ledger object assembly를 수행한다.
- save/write/release는 facade 쪽에 남기고, import-time HFSS object mutation과 summary assembly를 여기서 고정한다.

## 입력 / 출력
- 입력:
  - validated type2 STEP ledger
  - `HfssSession`
  - output/imported ledger paths
- 출력:
  - source paths, seed, imported ownership, imported object names만 담은 import-only `Type2ImportedLedger`
  - imported ledger JSON write helper

## Canonical state
- imported ledger runtime schema의 canonical owner다.
- imported ledger는 source paths, seed, imported ownership, imported object names를 보존한다.
- underlay exact-name solids는 STEP imported modeled bodies로 유지하고, port sheets는 metadata reconstruction 결과만 ledger에 append한다.
- 0.2.23 document contract에서는 TX `tx_underlay_*`와 RX `under_rx_*`를 role-aware imported solids로 취급한다.

## Invariants / fail-fast
- import diff는 exact-name / duplicate-free / non-empty여야 한다.
- modeled object styling 전에 TX/RX underlay exact-name presence를 보고 `MULL12060ferrite` / `PET_PSA` material setup를 조건부로 정확히 한 번 수행한다.
- port-sheet reconstruction은 metadata `port_sheet_vertices_xyz`를 canonical source로 삼는다.
- `AssignLengthOp`, `create_region`, `assign_radiation_boundary_to_faces`, `AssignLumpedPort`, `ValidateDesign()`는 여기서 호출하지 않는다.
- import-only 단계 실패는 scene import, partition, style/material, port-sheet reconstruction 범위에서만 surface된다.

## 직접 의존
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_runtime_common.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]

## 변경 시 주의점
- save/release ownership은 facade에 두고 core는 import-time HFSS mutation과 summary assembly만 담당한다.
- conductor material ownership과 underlay material ownership을 섞지 않는다. coil conductors는 `copper`, TX/RX underlay ferrite는 `MULL12060ferrite`, PET는 `PET_PSA`, air는 `vacuum`이다.
- scene-global underlay material prep는 modeled entry loop 바깥에서 한 번만 실행하고, per-entry styling은 exact imported solids mutation만 담당한다.
- port-sheet STEP ownership을 되살리지 않는다. canonical port sheets are reconstructed from metadata after STEP import.
