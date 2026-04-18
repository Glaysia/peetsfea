---
title: type2_step_import_style.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - hfss-import
  - aedt
---

# type2_step_import_style.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_style.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py.md`
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]
- Related feature plan: [[sdd/plans/0.2.23-type2-underlay-region-footprint-tx-gap-rx-support]]
- Parent note: [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 역할
- imported object model-state 고정, material/color styling, owner-fit placement validation, optional port-sheet HFSS reconstruction을 담당한다.
- notebook ferrite dataset(`notebooks/mu_p.tab`) import, project dataset 등록, raw definition manager 기반 underlay ferrite material(`MULL12060ferrite`) 정의/동기화 책임을 가진다.
- geometry repair 없이 export ledger placement truth를 검증만 수행한다.

## 입력 / 출력
- 입력: modeler/hfss session, validated ledger metadata, partitioned imported names
- 출력: styled imported objects, reconstructed canonical port-sheet names, validated placement state

## Canonical state
- non-model: gray/transparency + `model=False`.
- modeled PCB: `FR4_epoxy`/green + `model=True`.
- modeled coil conductor: exact `copper` + existing copper visual color.
- modeled TX/RX underlay ferrite body: exact `MULL12060ferrite`.
- modeled TX/RX underlay dielectric body: exact `PET_PSA`, with air-like dielectric baseline and documented `permittivity = 2.8`.
- modeled TX/RX underlay air body: explicit `vacuum`.
- modeled port sheet: STEP import object set에 존재하지 않는 것이 기본이며, terminal metadata의 canonical `port_sheet_vertices_xyz`로 HFSS에서 재생성한 sheet다. live AEDT object가 volume `Material` 속성을 노출할 때만 vacuum volume material mutation을 시도하고, 일반 sheet처럼 그 속성이 없으면 volume-material mutation은 건너뛴다.
- ferrite dataset canonical source는 `notebooks/mu_p.tab`, `$mu_r_real`, `$mu_tand_m` payload다.
- ferrite material canonical writer는 project `DefinitionManager.AddMaterial/EditMaterial`이며, geometry styling 전에 PyAEDT material lookup과 동기화돼야 한다.
- PET dielectric material canonical writer는 `materials.add_material("PET_PSA")`지만, geometry styling 전에 `material_keys` visibility까지 강제 동기화돼야 한다.
- underlay bodies are modeled solids but are neither conductor-mesh owners nor port-sheet reconstruction owners.
- role-aware TX/RX underlay material preparation is scene-global and runs once before modeled-body styling when any imported ferrite/PET/air underlay trio is present.

## Invariants / fail-fast
- PyAEDT `set_object_model_state` `False` return은 즉시 raise.
- ferrite dataset tab file 누락, raw design/project dataset API 누락, `ImportDataset` / `AddDataset` / raw `DefinitionManager` API 부재, material lookup sync 실패는 즉시 raise한다.
- required terminal metadata `port_sheet_vertices_xyz`, HFSS `create_polyline`, `cover_lines`, reconstructed sheet model-state mutation 실패도 즉시 raise한다. Volume `Material` 속성이 실제로 없는 sheet에 대해서는 그 mutation을 시도하지 않는다.
- TX/RX owner-fit mismatch는 move() repair 없이 즉시 raise.
- TX owner-fit validation은 `tx_region.min_x` touch + centered Y + max-Z touch를 그대로 요구한다.
- TX multilayer exact-name body set도 conductor-vs-underlay styling contract를 그대로 적용한다.
- TX/RX underlay exact-name bodies must not be restyled as copper or FR4, and explicit air bodies must remain `vacuum`.
- RX `under_rx_*` exact names use the same ferrite/PET/air styling contract as TX `tx_underlay_*`.

## 직접 의존
- `peetsfea.aedt.failfast`
- `peetsfea.aedt.proxies`
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 변경 시 주의점
- style/model-state와 import diff ownership resolution을 분리 유지한다.
- placement validation에서 fallback repair path를 넣지 않는다.
- notebook dataset-backed ferrite setup는 import 1회당 1회만 준비하도록 pipeline orchestration과 맞물려 유지한다.
- real AEDT에서 object `material_name` setter가 lookup 성공을 선행 조건으로 갖기 때문에, raw material definition write 후 PyAEDT material cache visibility를 반드시 보장해야 한다.
- real AEDT에서 `materials.add_material("PET_PSA")` 성공 뒤에도 `material_keys`가 늦게 채워질 수 있으므로 PET 경로도 explicit cache sync를 거친 뒤에만 property setter를 호출한다.
- free-surface imported FACE names를 신뢰하지 않는다. canonical port-sheet name은 runtime reconstruction 결과여야 하며, STEP export가 그 시트를 이미 포함한다고 가정하지 않는다.
- real AEDT covered-polyline port sheets can lack the volume `Material` property even though solids expose it; port-sheet styling must read `valid_properties` before issuing volume material mutation.
- underlay material ownership과 conductor material ownership을 섞지 않는다. `MULL12060ferrite`는 TX/RX underlay ferrite slabs에만 쓰고, coil conductors는 `copper`를 유지한다.
