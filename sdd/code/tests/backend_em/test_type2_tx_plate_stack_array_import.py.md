---
title: test_type2_tx_plate_stack_array_import.py
created: 2026-04-20 @ 04:35
updated: 2026-04-20 @ 15:25
tags:
  - tests
  - hfss-import
  - tx
  - plate-stack
---

# test_type2_tx_plate_stack_array_import.py

## Source
- Path: `tests/backend_em/test_type2_tx_plate_stack_array_import.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_tx_plate_stack_array_import.py.md`
- Status: planned
- Related plan: [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]]

## 역할
- TX plate-stack array import/setup-ready boundary를 검증한다.

## 입력 / 출력
- 입력: fake HFSS/modeler imported names and TX array ledger entries
- 출력: pytest assertions for import partition, material styling, group recreation, mesh target, port count, and EM input

## Canonical state
- Imported ledger has one `tx_plate_stack` modeled entry, one `rx_plate_stack` modeled entry.
- TX branch bodies remain owned by the single TX modeled entry.
- Connector sheet faces are not expected from fake STEP import batches; import core reconstructs them from
  `canonical_coordinates.connector_sheet_vertices_xyz_by_name`.
- TX array placement validation allows X overflow from rotated copied branches while still rejecting Z overflow.
- Setup-ready still assigns one TX excitation and one RX excitation.

## Invariants / fail-fast
- Missing branch ferrite/PCB names fail exact-name validation.
- Legacy segment leakage and generic `SOLID*` drift remain hard failures.
- Mesh target remains conductor-only: TX branch copper bodies plus TX connector sheet faces, and RX `rx_plate_copper`.
- Missing canonical connector sheet vertices is a stale-ledger/import-contract failure.
- Rotated TX array metadata must reconstruct exactly one shared `tx_plate_port_sheet`.

## 직접 의존
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_input.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py]]

## 관련 테스트
- This file is the direct import/setup regression owner.

## 변경 시 주의점
- Keep source/analysis expectations single-port unless a later plan explicitly changes EM excitation semantics.
