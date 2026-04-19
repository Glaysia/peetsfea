---
title: type2_step_post_import_mesh.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 23:59
tags:
  - hfss-import
  - mesh
---

# type2_step_post_import_mesh.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py.md`
- Status: active

## Ownership
- Primary plan: [[sdd/plans/0.2.22-type2-plate-stack-full-em]]
- TX array plan: [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]]
- RX-only active plan: [[sdd/plans/0.2.22-type2-rx-only-baseline]]
- Primary architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- setup-ready imported conductors에 mesh length operation을 할당한다.
- exact tx/rx role pair를 fail-fast로 검증하고, pair별 conductor mesh target을 canonical contract로 해석한다.

## 입력 / 출력
- 입력: HFSS session, imported modeled objects
- 출력: mesh summary

## Canonical state
- active helper path supports one-entry `['rx_single_coil']`.
- retained historical role-pair support must stay explicit where kept.
- TX array remains the same `['tx_plate_stack', 'rx_plate_stack']` exact pair.
- coil pair의 mesh target 해석은 기존과 동일하다.
  - TX: `tx_copper_l0` 또는 `tx_copper_stack` 중 정확히 하나
  - RX: `rx_copper_l0` 정확히 하나
- plate-stack pair는 conductor-only exact-name set을 imported exact-name order로 mesh target에 넣는다.
- RX-only mesh target list contains `rx_copper_l0` only.
- TX plate-stack pair는 single/array 모두 `tx_plate_copper`와 `rx_plate_copper`를 conductor mesh target으로 사용한다.
  개별 `*_copper_wall_t*`, `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_*`는 도체 mesh 대상이 아니다.
- Branch-local TX array intermediate copper bodies and connector bridges are fused before import and are not separate mesh targets.
- plate-stack mesh target에는 PCB, ferrite, underlay, reconstructed port sheet가 포함되지 않는다.
- legacy pre-unite segment(`*_copper_wall_t*`, `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_*`)는 final mesh 타겟으로 허용되지 않는다.

## Invariants / fail-fast
- active RX-only modeled_objects length is exactly 1 and role is exactly `rx_single_coil`.
- unsupported role sets, unsupported roles, and duplicate roles fail immediately.
- plate-stack entry에서 required concrete conductor members가 존재해야 한다. RX는 `rx_plate_copper` 정확히 1개다.
- plate-stack entry에서 pre-unite segment 라벨이 final conductor 목록에 남아 있으면 즉시 실패한다.
- `generic SOLID*` 이름은 즉시 실패한다.
- mesh target은 conductor-only이며 ferrite/pcb/air/port sheet를 제외한다.

## Collaborators
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_input.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]

## 변경 시 주의점
- coil mesh contract를 변경하지 않는다.
- plate-stack mesh contract는 imported exact-name order와 conductor-only 범위를 유지한다.
- fallback 없이 contract 위반을 즉시 예외로 중단한다.
