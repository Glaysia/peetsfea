---
title: type2_step_import_partition.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 23:58
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
- Related feature plan: [[sdd/plans/0.2.22-type2-tx-underlay-mull12060ferrite]]
- Parent note: [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 역할
- scene import diff를 non-model/member ownership과 modeled body ownership으로 partition한다.
- modeled exported body-name contract를 PCB/copper role set과 planned TX underlay exact-name set으로 resolve한다.
- import 전후 object name diff의 non-empty/duplicate-free 검증을 담당한다.
- current single-coil contract no longer expects `tx_port_sheet` / `rx_port_sheet` in STEP imported names. Those sheets are reconstructed later from terminal metadata.

## 입력 / 출력
- 입력: validated ledger payload, before/after import object names
- 출력:
- `new_imported_object_names`
- non-model names by object id
- modeled names by object id
- resolved PCB/copper body sets
- modeled STEP body ownership for PCB/copper plus explicit TX underlay bodies

## Canonical state
- modeled ownership source는 `expected_exported_body_names`.
- non-model ownership source는 `member_objects`.
- PCB/copper names remain required exact semantic owners.
- TX underlay exact names (`tx_underlay_ferrite_u{n}`, `tx_underlay_pet_psa_u{n}`, `tx_underlay_air_u{n}`) remain explicit modeled-body owners and must stay distinct from copper ownership.
- Port-sheet ownership is outside this partition layer and belongs to later reconstruction.

## Invariants / fail-fast
- imported names must be duplicate-free.
- unclaimed names, duplicate claims, missing required PCB/copper modeled body names are hard failures.
- generic `SOLID*` fallback resolution은 금지한다.
- TX multilayer (`tx_pcb_l{n}` + `tx_copper_stack`) exact-name contract를 유지한다.
- TX underlay bodies are part of the planned STEP imported-name contract here; partition/runtime must not treat them as implicit copper/PCB aliases.
- port-sheet bodies are not part of the STEP imported-name contract here; partition/runtime must not treat reconstructed sheets as imported body aliases.

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
- underlay exact-name taxonomy와 reconstructed sheet ownership을 섞지 않는다. underlay is imported; port sheet is reconstructed.
