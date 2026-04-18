---
title: type2_step_post_import_mesh.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 21:47
tags:
  - hfss-import
  - mesh
---

# type2_step_post_import_mesh.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py.md`
- Status: active
- Related feature plan: [[sdd/plans/0.2.25-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- setup-ready imported conductors에 mesh length operation을 할당한다.

## 입력 / 출력
- 입력: HFSS session, imported modeled objects
- 출력: mesh summary

## Canonical state
- current helper는 coil conductor mesh 전용이다.
- active plate roles는 direct helper call에서도 unsupported로 처리된다.

## Invariants / fail-fast
- plate roles에 conductor object candidate를 추론하려고 하면 안 된다.
- mesh target은 conductor-only이며 ferrite/pcb/air는 제외한다.

## Collaborators
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]

## 변경 시 주의점
- active plate roles를 임시 mesh candidate fallback으로 우회하지 않는다.
