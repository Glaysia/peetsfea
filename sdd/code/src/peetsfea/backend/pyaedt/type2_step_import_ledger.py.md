---
title: type2_step_import_ledger.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 02:20
tags:
  - hfss-import
  - import-only
---

# type2_step_import_ledger.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_ledger.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py.md`
- Status: active

## Ownership
- Primary plan: [[sdd/plans/0.2.22-type2-import-ledger-pipeline]]
- TX array plan: [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]]
- Primary architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- exported step ledger JSON을 import-only runtime이 신뢰할 수 있는 validated shape로 정규화한다.

## 입력 / 출력
- 입력: `type2_step_ledger.json`
- 출력: validated step ledger object, validated modeled/non-model entries

## Canonical state
- import-only path는 `tx_plate_stack`, `rx_plate_stack`, legacy single-coil roles를 모두 읽을 수 있다.
- plate roles terminal metadata는 `kind = "stub_port"`와 stub body name / plane point / sheet vertices를 유지한다.
- setup-ready/mesh/port/EM rejection은 downstream stage의 책임이며, 여기서는 import-only acceptance를 우선한다.
- plate-stack의 export-side `tx_copper_wall_t*`, `tx_copper_coil_t*`, `tx_bridge_s*`, `tx_stub_in/out`,
  `rx_copper_wall_t*`, `rx_copper_coil_t*`, `rx_bridge_s*`, `rx_stub_in/out`는 pre-unite provenance로만 취급한다.
- final import ledger의 single-branch plate-stack 도체는 `tx_plate_copper`, `rx_plate_copper` 단일 body다.
  TX array 도체는 `tx_b{i}_plate_copper` branch bodies와 input/output connector sheet faces다.
- ferrite grouping contract는 per-`uN` sandwich가 아니라 role-family 단일 그룹이다: TX=`g_ferrite_tx`, RX=`g_ferrite_rx`.
- active plate-stack roles의 ferrite group member contract는 merged exact-name 3개다:
  TX=`tx_stack_pet_psa`, `tx_stack_ferrite`, `tx_stack_air`;
  RX=`rx_stack_pet_psa`, `rx_stack_ferrite`, `rx_stack_air`.
- expected_imported_body_groups는 role 단위로 항상 `g_copper_tx`/`g_copper_rx` 및 `g_ferrite_tx`/`g_ferrite_rx`를 포함해야 한다.
- TX arrays allow branch-local ferrite-family body names and branch-local/sheet copper members.
- single-coil roles는 기존 underlay/wall prefix family contract를 유지한다.
- copper grouping contract는 plate-stack role별 단일 그룹을 사용한다:
  TX=`g_copper_tx`, RX=`g_copper_rx`;
  RX는 `member_names == ['rx_plate_copper']`, single TX는 `member_names == ['tx_plate_copper']`,
  TX array는 branch copper bodies와 connector sheet faces를 ordered member set으로 가진다.
- ferrite grouping contract은 TX/RX 각각 `g_ferrite_tx`, `g_ferrite_rx` 단일 그룹을 기대하며
  멤버 순서는 `pet_psa -> ferrite -> air`로 strict하게 고정한다.
- final imported conductor 후보가 없거나 `g_copper_*` 그룹이 재생성되지 않으면 hard failure다.

## Invariants / fail-fast
- required ledger keys와 retained `outputs`는 exact contract를 따라야 한다.
- modeled expected body names/count mismatch는 hard failure다.
- plane, owner id, source metadata path는 non-empty validated state여야 한다.
- modeled ferrite groups는 legacy single-coil role에서는 0개(해당 ferrite family 없음) 또는 정확히 1개만 허용하고,
  plate-stack 역할에서는 `g_ferrite_tx`/`g_ferrite_rx`가 정확히 1개씩 있어야 한다.
- modeled copper groups는 role별로 정확히 1개만 허용하며 required concrete copper members가 반드시 포함되어야 한다.
- modeled copper/ferrite contract은 role별로 `g_copper_*`와 `g_ferrite_*` 모두 존재해야 하며,
  하나라도 누락되면 즉시 hard failure다.
- ferrite family가 존재하면 group name/member set/member order mismatch는 즉시 실패한다.
- plate-stack roles에서는 old `*_stack_*_uN` ferrite-family naming을 허용하지 않는다.
- legacy segment labels(`*_copper_wall_t*`, `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_*`)를 final 도체로 간주하면 즉시 실패한다.
- generic `SOLID*` 드리프트는 import ledger 단계에서 치유 없이 즉시 실패한다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]

## 변경 시 주의점
- import-only acceptance와 setup-ready rejection 책임을 한 함수 안에 다시 섞지 않는다.
- plate-stack terminal metadata validation은 direct EM enablement가 아니라 import-only sheet reconstruction precondition이다.
