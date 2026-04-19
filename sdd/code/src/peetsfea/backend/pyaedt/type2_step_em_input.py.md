---
title: type2_step_em_input.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 23:59
tags:
  - hfss-import
  - em
---

# type2_step_em_input.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_em_input.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_input.py.md`
- Status: active

## Ownership
- Primary plan: [[sdd/plans/0.2.22-type2-plate-stack-full-em]]
- TX array plan: [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]]
- RX-only active plan: [[sdd/plans/0.2.22-type2-rx-only-baseline]]
- Primary architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 단일 책임
- validated imported ledger(+assigned ports)를 role-exact EM pipeline payload로 정규화한다.

## 입력 / 출력
- 입력: imported ledger, `EmPorts`
- 출력: `EmPipelineInput`

## Canonical state
- direct EM input active role set is one-entry `rx_single_coil`.
- retained historical role-pair support must remain explicit where kept and must not create a TX fallback for RX-only inputs.
- TX array still appears as the same exact pair: one `tx_plate_stack` entry and one `rx_plate_stack` entry.
- plate-stack endpoint는 `stub_port` metadata(`start_point_plane_mm`, `end_point_plane_mm`)와 modeled plane(`YZ`) 기반 world 좌표로 생성한다.
- RX-only maps only the RX endpoint as `rx_dd`.
- plate-stack endpoint label은 semantic stub label(`input_stub`, `output_stub`)을 사용한다.
- ready object 구성은 role-local body 분류를 사용한다.
  - conductor: plate-stack은 single/array 모두 `tx_plate_copper` 또는 `rx_plate_copper`
  - fr4: role-local PCB bodies
  - ferrite: empty list
- TX array conductor name is the exported united `tx_plate_copper`; branch-local PCB/ferrite bodies must not add TX
  conductors or ports.
- pre-unite segment 이름(`*_copper_wall_t*`, `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_*`)은 ready conductor에서 제외된다.

## Invariants / fail-fast
- active RX-only modeled object는 정확히 1개여야 하며, retained pair modes are explicit where still supported.
- duplicated role or unsupported role sets fail immediately.
- coil role의 imported names는 `>=1 PCB + exactly 1 copper` contract를 강제한다.
- RX-only role requires one or more RX PCB names and exactly one `rx_copper_l0` conductor.
- plate-stack role은 PCB bodies와 ready conductor set을 사용한다. TX/RX conductors are exactly
  `tx_plate_copper` / `rx_plate_copper` for new plate-stack array exports.
- plate-stack role의 ready conductor가 concrete exported copper member가 아니거나 legacy segment(`*_copper_wall_t*`,
  `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_*`)가 남아 있으면 즉시 실패한다.
- plate-stack EM target은 concrete exported copper members만 허용하며 개별 pre-unite copper family segment가 남아 있으면 즉시 실패한다.
- generic `SOLID*` pre/post-unite 이름 drift는 즉시 실패한다.
- plate-stack endpoint는 `terminal_metadata.kind == "stub_port"` 및 `plane == "YZ"`를 강제한다.

## Collaborators
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_port_assignment.py]]
- [[sdd/code/src/peetsfea/types/geometry.py]]
- [[sdd/code/src/peetsfea/types/runtime_selection.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]

## 변경 시 주의점
- coil endpoint semantics(`outer_corner`/`inner_corner`, group_kind mapping)는 유지해야 한다.
- plate-stack conductor set은 concrete copper members만 포함해야 하며 PCB/underlay를 섞으면 안 된다.
- plate-stack endpoint world 변환은 plane contract(YZ)을 우회하거나 fallback으로 대체하면 안 된다.
- setup-ready facade ownership(경계/포트/해석/저장)은 그대로 유지해야 한다.
