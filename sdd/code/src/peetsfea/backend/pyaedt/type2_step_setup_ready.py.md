---
title: type2_step_setup_ready.py
created: 2026-04-17 @ 09:09
updated: 2026-04-20 @ 23:59
tags:
  - hfss-import
  - em
---

# type2_step_setup_ready.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_setup_ready.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py.md`
- Status: active

## Ownership
- Primary plan: [[sdd/plans/0.2.22-type2-plate-stack-full-em]]
- RX-only active plan: [[sdd/plans/0.2.22-type2-rx-only-baseline]]
- Primary architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- type2 role-aware setup facade다.
- import-only handoff 이후 modeled role family에 따라
  - coil full setup-ready
  - plate-stack full setup-ready
  branch를 orchestrate한다.

## 입력 / 출력
- 입력: step ledger path, output/imported-ledger paths, optional design variables, optional attached HFSS session
- 출력: exact coil/plate-stack pair 모두 `Type2SetupReadyResult`

## Canonical state
- preflight는 step ledger load 직후, HFSS launch 전에 수행된다.
- exact coil pair는 current full setup-ready path를 유지한다.
- exact plate-stack pair도 coil pair와 동일하게 full setup-ready pipeline을 수행한다.
- active RX-only role set `rx_single_coil` performs the full setup-ready pipeline without a TX placeholder.
- malformed role sets are rejected before HFSS launch.
- plate-stack branch는 `tx_plate_port_sheet` / `rx_plate_port_sheet` 재구성 체인을 그대로 보존하고 stub_port metadata를 downstream EM/mesh 단계까지 전달한다.
- geometry-view import-only는 sibling import pipeline의 책임으로 계속 남는다.
- setup-ready는 stable imported name contract를 소비하는 단계이며 geometry heal/subtract/repair ownership이 없다.
- non-overlap export 이후에도 setup-ready의 runtime boundary는 기존 exact-name/port-sheet reconstruction contract다.

## Invariants / fail-fast
- plate-stack branch도 post-import mesh, EM input/grouping/series/subtract, source phase, analysis/report, validate_pipeline, ValidateDesign, final save를 수행한다.
- mixed TX plate-stack/RX single-coil branch도 동일 후반 체인을 수행하며 reduced setup으로 분기하지 않는다.
- RX-only EM input requires `rx_copper_l0` as the RX conductor ready object and no TX conductor placeholder.
- RX-only explicit port contract uses reconstructed `rx_port_sheet` and fixed numeric `1/1_T1`.
- unsupported message는 mesh/EM helper와 의미를 맞춘다.
- import-only helper direct call과 setup facade branch는 서로 다른 ownership을 유지한다.
- plate-stack branch는 imported bridge/slab/copper geometry를 boolean clean-up 하거나 재구성하지 않는다.

## Collaborators
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_port_assignment.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_input.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]
- [[sdd/code/tests/type2/test_build_type2_entry.py]]

## 변경 시 주의점
- branch selection을 HFSS 생성 이후로 늦추지 않는다.
- plate-stack exact pair를 reduced partial-setup contract로 되돌리지 않는다.
- setup-ready 경로에 geometry-repair fallback을 추가하지 않는다.
