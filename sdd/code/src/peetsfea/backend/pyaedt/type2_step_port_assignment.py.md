---
title: type2_step_port_assignment.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 23:59
tags:
  - hfss-import
  - port
---

# type2_step_port_assignment.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_port_assignment.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_port_assignment.py.md`
- Status: active
- Related feature plan: [[sdd/plans/0.2.22-type2-tx-rx-shared-plate-stack-import-only]]
- Related TX array plan: [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]]
- Related RX-only plan: [[sdd/plans/0.2.22-type2-rx-only-baseline]]

## 역할
- setup/runtime imported objects에 explicit lumped port를 할당한다.

## 입력 / 출력
- 입력: HFSS session, modeler, imported ledger
- 출력: `EmPorts`

## Canonical state
- helper는 reconstructed port-sheet ownership을 사용한다.
  - coil: `tx_port_sheet` / `rx_port_sheet`
  - plate-stack: `tx_plate_port_sheet` / `rx_plate_port_sheet`
- TX array still reconstructs one `tx_plate_port_sheet` and assigns one TX terminal port.
- active RX-only path uses `rx_port_sheet` for RX and creates no TX port placeholder.

## Invariants / fail-fast
- active direct assignment preflight accepts exactly one `rx_single_coil` entry.
- active one-entry `rx_single_coil` support is explicit; retained pair support remains historical/component coverage.
- `tx_single_coil` + `rx_plate_stack` remains unsupported.
- `terminal_metadata.kind == "stub_port"` roles는 metadata vertices와 reconstructed sheet가 모두 있어야 한다.
- RX-only numeric boundary/excitation naming은 `1` / `1_T1` 고정이다.
- plate roles를 coil endpoint fallback으로 취급하면 안 된다.
- Parallel TX branches do not create per-branch port assignments in this plan.

## Collaborators
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_input.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]

## 변경 시 주의점
- direct port helper 확장은 EM input helper 확장과 분리해서 유지한다.
