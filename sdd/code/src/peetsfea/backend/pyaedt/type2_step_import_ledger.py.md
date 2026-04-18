---
title: type2_step_import_ledger.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 21:45
tags:
  - hfss-import
  - import-only
---

# type2_step_import_ledger.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_ledger.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py.md`
- Status: active
- Related feature plan: [[sdd/plans/0.2.25-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- exported step ledger JSON을 import-only runtime이 신뢰할 수 있는 validated shape로 정규화한다.

## 입력 / 출력
- 입력: `type2_step_ledger.json`
- 출력: validated step ledger object, validated modeled/non-model entries

## Canonical state
- import-only path는 `tx_plate_stack`, `rx_plate_stack`, legacy single-coil roles를 모두 읽을 수 있다.
- geometry-only plate roles terminal metadata는 `{"kind": "none"}` sentinel로 유지된다.
- setup-ready/mesh/port/EM rejection은 downstream stage의 책임이며, 여기서는 import-only acceptance를 우선한다.

## Invariants / fail-fast
- required ledger keys와 retained `outputs`는 exact contract를 따라야 한다.
- modeled expected body names/count mismatch는 hard failure다.
- plane, owner id, source metadata path는 non-empty validated state여야 한다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]

## 변경 시 주의점
- import-only acceptance와 setup-ready rejection 책임을 한 함수 안에 다시 섞지 않는다.
