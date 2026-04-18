---
title: type2_step_port_assignment.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 21:47
tags:
  - hfss-import
  - port
---

# type2_step_port_assignment.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_port_assignment.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_port_assignment.py.md`
- Status: active
- Related feature plan: [[sdd/plans/0.2.25-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- setup-ready coil imported objects에 lumped port를 할당한다.

## 입력 / 출력
- 입력: HFSS session, modeler, imported ledger
- 출력: `EmPorts`

## Canonical state
- 현재 helper는 `tx_single_coil` / `rx_single_coil` exact pair 전용이다.
- active plate roles는 port-sheet를 갖지 않으므로 direct helper call에서도 unsupported다.

## Invariants / fail-fast
- `terminal_metadata.kind == "none"` role에 port-sheet vertices를 요구하면 안 된다.
- plate roles를 coil endpoint fallback으로 취급하면 안 된다.

## Collaborators
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_input.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]

## 변경 시 주의점
- active plate roles에 synthetic sheet를 만들어 setup-ready를 통과시키지 않는다.

