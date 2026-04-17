---
title: type2_modeled_import_adapter.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 19:20
tags:
  - type2
  - hfss-import
  - aedt
---

# type2_modeled_import_adapter.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py.md`
- Related plan: [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]]
- Related architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]
- Upstream metadata producer: [[sdd/code/entry/generate_type2_step.py]]

## 역할
- type2 STEP ledger의 modeled entry와 single scene STEP import 결과 `imported_object_names`를 합쳐 single imported modeled-object ledger entry를 만든다.
- 현재 single-coil prototype(`role=tx_single_coil | rx_single_coil`)을 허용하는 fail-fast adapter 계약을 제공한다.

## 입력 / 출력
- 입력:
  - `modeled_object: dict[str, object]` (from type2 STEP ledger `modeled_objects[*]`)
  - `imported_object_names: Sequence[str]`
- 출력:
  - `ImportedModeledObjectEntry` typed contract
  - 필수 필드: `object_id`, `role`, `material`, `model_state`, `canonical_coordinates`, `terminal_metadata`, `imported_object_names`

## Canonical state
- module-level mutable state는 없다.
- canonical source of role/coordinates/terminal semantics is metadata `modeled_object`.
- AEDT import side에서 canonical source는 `imported_object_names` only.
- exact-name STEP import contract is PCB/copper plus planned TX underlay solids only.
- runtime may later append reconstructed `tx_port_sheet` / `rx_port_sheet` names to imported ownership, but those sheets are metadata-driven reconstruction results rather than STEP imported body names.

## Invariants / fail-fast
- `modeled_object.role` must be `tx_single_coil` 또는 `rx_single_coil`.
- `modeled_object.plane` must be `XY` 또는 `YZ`.
- `modeled_object.placement_owner_id`는 non-empty string이어야 한다.
- `modeled_object.model_state` must be `True`.
- `canonical_coordinates`와 `terminal_metadata` required keys가 없으면 즉시 실패한다.
- coordinate/path/terminal field는 타입과 최소 shape(길이, non-empty string)를 강제한다.
- `imported_object_names`는 non-empty, all-string, duplicate-free여야 한다.
- AEDT geometry reverse-calculation은 하지 않는다.
- imported reconstructed port-sheet names, when present, are preserved as runtime-owned reconstructed names; this adapter does not project lumped-port assignment from them yet.

## 직접 의존
- 표준 라이브러리: `typing`, `collections.abc`

## 이 파일을 쓰는 곳
- 다음 단계 modeled import smoke path에서 imported ledger entry 생성 경계로 사용된다.

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_modeled_import_adapter.py]]

## TODO
- [ ] imported entry가 direct `EmPipelineInput` 조립에 필요한 terminal/ownership projection까지 맡을지 결정한다.
- [ ] role-neutral public naming이 정리되면 adapter fixture/object id naming도 함께 정리한다.
- [ ] setup-ready slice에서 port candidate metadata를 adapter output에 포함할지 검토한다.
- [ ] imported exact-name contract의 PCB/copper/TX-underlay solids와 reconstructed port-sheet names를 분리한 future port-candidate projection shape를 확정한다.

## 변경 시 주의점
- single-coil 제약을 완화해 multi-object adapter로 확장할 때는 role taxonomy와 imported-name ownership 규칙을 별도 계획으로 고정해야 한다.
- metadata schema field 이름이나 좌표 의미를 바꾸면 upstream `tx_rect_void` export와 이 adapter를 동시에 갱신한다.
