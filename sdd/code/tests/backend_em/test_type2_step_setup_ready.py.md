---
title: test_type2_step_setup_ready.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - hfss-import
  - em
---

# test_type2_step_setup_ready.py

## Source
- Path: `tests/backend_em/test_type2_step_setup_ready.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_step_setup_ready.py.md`
- Tested source:
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_input.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_port_assignment.py]]

## 역할
- type2 setup-ready runtime을 pure-Python fake HFSS seam으로 검증한다.
- mesh, radiation boundary, explicit ports, source/analysis/report, `ValidateDesign()` call order와 fail-fast를 검증한다.
- sampled build caller가 준 AEDT design variable handoff도 같은 fake HFSS seam에서 검증한다.
- direct mesh-helper seam을 통해 future role-aware RX underlay imported-name contract도 pure-Python으로 고정한다.
- TX floor-underlay exact names는 더 이상 setup-ready imported-name helper에 포함되지 않는다.
- TX wall-parallel underlay regression도 shared imported-name helper contract 위에서 conductor-only mesh invariants를 유지해야 한다.

## 입력 / 출력
- 입력:
  - test-local STEP placeholder
  - test-local STEP ledger JSON
  - fake HFSS/modeler/boundary/report seams
- 출력:
  - `Type2SetupReadyResult`
  - fake call history

## Canonical state
- fake call history lists와 import handoff가 persisted한 imported ledger `mesh` / `boundary` summary가 canonical assertion surface다.

## Invariants / fail-fast
- import core handoff 이후 realized `mesh` / `boundary` summary를 그대로 사용한 채 `AssignLumpedPort`, sources, analysis, `ValidateDesign()`, save 순서가 유지되어야 한다.
- report/output-variable creation은 retained step ledger top-level `outputs`를 source로 사용해야 한다.
- attached-session path도 same setup-ready contract를 공유해야 한다.
- setup-ready mesh coverage는 TX `tx_copper_l0`뿐 아니라 multilayer `tx_copper_stack` conductor path도 검증해야 한다.
- TX wall exact-name bodies가 full setup-ready path에 들어와도 mesh target은 conductor-only여야 한다.
- future RX role-aware import contract에서도 RX underlay exact-name bodies와 TX wall exact-name bodies는 setup-ready mesh target과 port ownership 바깥에 남아야 한다.
- missing copper names, missing/malformed port sheet vertices, edge mismatch, `AssignLumpedPort` false, boundary false, `ValidateDesign` false는 즉시 raise다.
- caller-provided design variables는 import/save 이전에 HFSS session에 그대로 반영되어야 한다.

## 직접 의존
- `pytest`
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]

## 이 파일을 쓰는 곳
- Default pure-Python test suite.

## 관련 테스트
- This file is the direct test coverage for the type2 setup-ready runtime split.

## 변경 시 주의점
- real AEDT launch를 추가하지 않는다.
- import-only assertions를 이 파일에 섞지 않는다.
- RX underlay 지원을 앞당겨 검증할 때도 import partition/style ownership 자체는 이 파일에서 다시 구현하지 않는다.
