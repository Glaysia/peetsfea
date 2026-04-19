---
title: type2_step_post_import_mesh.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 00:32
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
- Primary architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- setup-ready imported conductors에 mesh length operation을 할당한다.
- exact tx/rx role pair를 fail-fast로 검증하고, pair별 conductor mesh target을 canonical contract로 해석한다.

## 입력 / 출력
- 입력: HFSS session, imported modeled objects
- 출력: mesh summary

## Canonical state
- helper는 exact pair `['tx_single_coil', 'rx_single_coil']` 또는 `['tx_plate_stack', 'rx_plate_stack']`만 지원한다.
- coil pair의 mesh target 해석은 기존과 동일하다.
  - TX: `tx_copper_l0` 또는 `tx_copper_stack` 중 정확히 하나
  - RX: `rx_copper_l0` 정확히 하나
- plate-stack pair는 conductor-only exact-name set을 imported exact-name order로 mesh target에 넣는다.
  - `*_copper_wall_t*`
  - `*_copper_coil_t*`
  - `*_bridge_s*`
  - `*_stub_in`
  - `*_stub_out`
- plate-stack mesh target에는 PCB, underlay, reconstructed port sheet가 포함되지 않는다.

## Invariants / fail-fast
- modeled_objects는 정확히 2개여야 하며 중복 없는 exact tx/rx pair여야 한다.
- mixed role family(coil+plate), unsupported role, duplicate role은 즉시 실패한다.
- plate-stack entry는 각 required copper family를 충족해야 한다.
  - wall/coil/bridge: role-local prefix 기준 1개 이상
  - stub_in/stub_out: role-local exact name 각각 정확히 1개
- plate-stack entry에서 role-local `copper_/bridge_/stub_` 이름 중 contract 밖 body가 있으면 즉시 실패한다.
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
