---
title: type2_step_import_partition.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 17:20
tags:
  - type2
  - hfss-import
  - aedt
---

# type2_step_import_partition.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_partition.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py.md`
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]
- Parent note: [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 역할
- scene import diff를 non-model/member ownership과 modeled exact-name body ownership으로 partition한다.
- modeled exported body-name contract를 PCB/copper role set으로 resolve한다.
- import 전후 object name diff의 non-empty/duplicate-free 검증을 담당한다.
- current single-coil exact-name contract also preserves the two modeled sheet bodies `tx_port_sheet`, `rx_port_sheet`.

## 입력 / 출력
- 입력: validated ledger payload, before/after import object names
- 출력:
  - `new_imported_object_names`
  - non-model names by object id
  - modeled names by object id
  - resolved PCB/copper body sets
  - exact-name participation of port-sheet bodies without collapsing them into PCB/copper styling ownership

## Canonical state
- modeled ownership source는 `expected_exported_body_names`.
- non-model ownership source는 `member_objects`.

## Invariants / fail-fast
- imported names must be duplicate-free.
- unclaimed names, duplicate claims, missing expected modeled body names are hard failures.
- generic `SOLID*` fallback resolution은 금지한다.
- TX multilayer (`tx_pcb_l{n}` + `tx_copper_stack`) exact-name contract를 유지한다.
- current single-layer exact-name contract includes `tx_port_sheet` and `rx_port_sheet`.
- port-sheet bodies remain separate modeled names; partition/runtime must not treat them as implicit copper/PCB aliases.

## 직접 의존
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 변경 시 주의점
- ownership partition과 visual styling을 다시 한 함수군에 섞지 않는다.
- exported exact-name contract가 바뀌면 export side와 이 모듈을 같이 갱신한다.
- future sheet-body import support must keep exact-name ownership and styling ownership separate.
