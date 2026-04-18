---
title: type2_step_setup_ready.py
created: 2026-04-17 @ 09:09
updated: 2026-04-19 @ 21:47
tags:
  - hfss-import
  - em
---

# type2_step_setup_ready.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_setup_ready.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py.md`
- Status: active
- Related feature plan: [[sdd/plans/0.2.25-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- type2 setup-ready facade다.
- import-only handoff 이후 mesh, boundary, port, source, analysis, validation, save를 orchestrate한다.

## 입력 / 출력
- 입력: step ledger path, output/imported-ledger paths, optional design variables, optional attached HFSS session
- 출력: `Type2SetupReadyResult`

## Canonical state
- active plate-stack example에서는 이 runtime이 unsupported preflight gate owner다.
- preflight는 step ledger load 직후, HFSS launch 전에 수행된다.
- geometry-view import-only는 sibling import pipeline의 책임이다.

## Invariants / fail-fast
- `tx_plate_stack` 또는 `rx_plate_stack`가 있으면 즉시 실패한다.
- unsupported message는 mesh/port/EM helper와 의미를 맞춘다.
- import-only acceptance를 이 facade 안에서 암묵적으로 우회하지 않는다.

## Collaborators
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_port_assignment.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_input.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]
- [[sdd/code/tests/type2/test_build_type2_entry.py]]

## 변경 시 주의점
- plate-role unsupported preflight를 import-only ledger loader 쪽으로 다시 밀어 넣지 않는다.
