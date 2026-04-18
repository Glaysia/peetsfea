---
title: type2_step_port_assignment.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - port
  - aedt
---

# type2_step_port_assignment.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_port_assignment.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_port_assignment.py.md`
- Related architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- reconstructed `tx_port_sheet` / `rx_port_sheet`에서 explicit lumped port를 만든다.
- vertex-order-based canonical edge selection, numeric boundary naming, excitation capture를 소유한다.

## 입력 / 출력
- 입력:
  - `HfssSession`
  - `ModelerSession`
  - imported modeled ledger entries
- 출력:
  - `EmPorts`

## Canonical state
- current type2 setup-ready explicit port assignment contract의 canonical owner다.
- edge ownership은 `port_sheet_vertices_xyz` ordering 기준이다.

## Invariants / fail-fast
- signal/start edge는 `(v3, v0)`, reference/end edge는 `(v1, v2)`다.
- TX boundary/excitation는 `1` / `1_T1`, RX는 `2` / `2_T1`다.
- sheet edge resolution은 exactly one match여야 한다.
- `AssignLumpedPort` false, excitation mismatch, missing sheet body는 즉시 raise다.

## 직접 의존
- `peetsfea.aedt.proxies`
- `peetsfea.backend.pyaedt.em_pipeline.steps.excitation_names`
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]

## 변경 시 주의점
- type1 helper를 수정하거나 ownership을 legacy module로 다시 밀어넣지 않는다.
- port edge semantics를 바꾸면 export-side vertex ordering assumptions와 tests를 함께 갱신한다.

