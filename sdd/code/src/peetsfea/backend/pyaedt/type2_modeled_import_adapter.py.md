---
title: type2_modeled_import_adapter.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 21:45
tags:
  - hfss-import
  - adapter
---

# type2_modeled_import_adapter.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py.md`
- Status: active
- Related feature plan: [[sdd/plans/0.2.25-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- modeled export entry와 imported object names를 imported-ledger modeled entry로 변환한다.

## 입력 / 출력
- 입력: exported modeled entry, imported object names
- 출력: typed imported modeled entry

## Canonical state
- legacy single-coil role은 full terminal metadata를 파싱한다.
- `tx_plate_stack`와 `rx_plate_stack`는 role-aware geometry-only sentinel `{"kind": "none"}`만 허용한다.
- canonical coordinates는 export ledger shape를 그대로 따른다.

## Invariants / fail-fast
- plate roles에서 coil terminal keys를 요구하면 안 된다.
- coil roles에서 sentinel-only metadata를 허용하면 안 된다.
- imported object names는 non-empty, duplicate-free exact set이어야 한다.

## Collaborators
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_modeled_import_adapter.py]]

## 변경 시 주의점
- `terminal_metadata.kind` 분기를 fallback parsing으로 흐리면 안 된다.
