---
title: type2_step_post_import_mesh.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 23:30
tags:
  - type2
  - mesh
---

# type2_step_post_import_mesh.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py.md`
- Related architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- import runtime shared helper로서 post-import mesh assignment를 소유한다.
- current exact contract `tx_copper_l0` or `tx_copper_stack` + `rx_copper_l0` / `Length1` / `MaxLength=5mm` / `NumMaxElem=1000`를 고정한다.

## 입력 / 출력
- 입력:
  - `HfssSession`
  - imported modeled ledger entries
- 출력:
  - mesh summary

## Canonical state
- mesh summary의 canonical owner다.

## Invariants / fail-fast
- TX mesh target은 exact imported names `tx_copper_l0` 또는 `tx_copper_stack` 중 하나여야 하고, RX mesh target은 exact `rx_copper_l0`여야 한다.
- `AssignLengthOp` false는 즉시 raise다.
- underlay exact-name bodies와 reconstructed port sheets는 mesh 대상에 들어가지 않는다.

## 직접 의존
- `peetsfea.aedt.protocols`
- `peetsfea.aedt.failfast`
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]

## 변경 시 주의점
- TX mesh target generalization은 conductor-only ownership을 유지한 채 움직여야 한다. `tx_copper_stack`을 허용하더라도 underlay bodies를 mesh set에 섞지 않는다.
