---
title: type2_step_import_core.py
created: 2026-04-19 @ 17:35
updated: 2026-04-22 @ 04:05
tags:
  - hfss-import
  - core
---

# type2_step_import_core.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_core.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py.md`
- Status: active

## Ownership
- Primary plan: [[sdd/plans/0.2.22-type2-import-ledger-pipeline]]
- TX array plan: [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]]
- Primary architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- scene STEP를 HFSS에 import하고 partition/style/adapter를 조합해 imported ledger를 만든다.

## 입력 / 출력
- 입력: `HfssSession`, step ledger path, output/imported-ledger paths, validated step ledger
- 출력: `Type2ImportedLedger`

## Canonical state
- import core는 geometry-view import-only owner다.
- Scene STEP import for new TX arrays expects the connector bridges to already be fused into `tx_plate_copper`;
  no TX array connector sheet reconstruction is required for newly generated ledgers.
- Scene STEP import requests no AEDT import group creation; if AEDT still reports wrapper names matching the scene STEP stem,
  core removes only those non-ledger wrapper names before exact-name partitioning.
- active plate roles도 imported ledger modeled entry로 남긴다.
- imported ledger는 export ledger contract를 유지하면서 import-only 전 과정에서 다음을 강제한다:
  - final single-branch plate-stack 도체 단일 바디: `tx_plate_copper`, `rx_plate_copper`
  - TX array conductor member: `tx_plate_copper`
  - copper group recreation: `g_copper_tx -> concrete TX conductor members`,
    `g_copper_rx -> ['rx_plate_copper']`
  - ferrite group recreation: `g_ferrite_tx -> TX exact branch ferrite-family members`,
    `g_ferrite_rx -> ['rx_stack_pet_psa', 'rx_stack_ferrite', 'rx_stack_air']`.
  - role 그룹 재생성은 `expected_exported_body_groups`의 동일 멤버와 순서와 일치해야 하며
    `g_copper_*`와 `g_ferrite_*` 누락은 즉시 실패다.
  - plate-stack modeled entries는 import 루프에서 export contract label list 전체가 유지되는지 먼저 검증하고,
    import-time에 final merged 도체/그룹 재구성을 확인한다.
- final conductor는 pre-unite segment family(`*_copper_wall_t*`, `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_*`) 대신
  concrete exported copper members로 정규화한다.
- `tx_rect_void_columns` owner-fit validation uses the union bounds of concrete `tx_region_actual_stack_space_*` members
  when the placement owner is tiled.

## Invariants / fail-fast
- scene import가 새 HFSS objects를 만들지 않으면 실패한다.
- wrapper-name normalization must never remove names present in the ledger-owned expected scene name set.
- New TX array ledgers must not require `canonical_coordinates.connector_sheet_vertices_xyz_by_name`; connector bridge
  provenance may be recorded for audit, but concrete import partitioning uses `tx_plate_copper`.
- owner-fit validation과 style application이 끝난 뒤 adapter entry를 만든다.
- plate-stack role에서 `expected_exported_body_names`/`expected_exported_body_groups`가 export-side contract와 다르면
  import 전에 즉시 실패한다.
- plate-stack role에서 required concrete copper members가 누락되거나 `g_copper_tx`/`g_copper_rx`,
  `g_ferrite_tx`/`g_ferrite_rx`가 누락되면 즉시 실패한다.
- TX array imported ledger must still contain one `tx_plate_stack` modeled entry, with `tx_plate_copper` preserved as
  the only TX conductor member.
- legacy final segment label(`*_copper_wall_t*`, `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_*`)이 도체 계약으로 남아 있으면 즉시 실패한다.
- generic `SOLID*` drift는 import repair 없이 즉시 실패한다.
- ferrite group recreation은 styling 직후, imported ledger merge 전에 실행한다.
- group recreation 결과 이름은 요청한 고정 group name과 일치해야 한다.
- setup-ready semantics는 여기서 실행하지 않는다.
- concrete tiled owner union must remain deterministic and must not synthesize fallback geometry; it only summarizes ledger-owned members.

## Collaborators
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 변경 시 주의점
- imported ledger write 책임을 setup-ready와 다시 섞지 않는다.
