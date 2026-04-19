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
- ferrite grouping contract는 per-`uN` sandwich가 아니라 role-family 단일 그룹이다: TX=`g_ferrite_tx`, RX=`g_ferrite_rx`.
- active plate-stack roles의 ferrite group member contract는 merged exact-name 3개다:
  TX=`tx_stack_pet_psa`, `tx_stack_ferrite`, `tx_stack_air`;
  RX=`rx_stack_pet_psa`, `rx_stack_ferrite`, `rx_stack_air`.
- single-coil roles는 기존 underlay/wall prefix family contract를 유지한다.

## Invariants / fail-fast
- required ledger keys와 retained `outputs`는 exact contract를 따라야 한다.
- modeled expected body names/count mismatch는 hard failure다.
- plane, owner id, source metadata path는 non-empty validated state여야 한다.
- modeled ferrite groups는 role별로 0개(해당 ferrite family 없음) 또는 정확히 1개만 허용한다.
- ferrite family가 존재하면 group name/member set/member order mismatch는 즉시 실패한다.
- plate-stack roles에서는 old `*_stack_*_uN` ferrite-family naming을 허용하지 않는다.

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
