---
title: type2_step_import_pipeline.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 21:45
tags:
  - hfss-import
  - pipeline
---

# type2_step_import_pipeline.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py.md`
- Status: active
- Related feature plan: [[sdd/plans/0.2.22-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- import-only AEDT generation facade다.
- active plate-stack geometry-view의 canonical runtime entry를 제공한다.

## 입력 / 출력
- 입력: step ledger path, output `.aedt` path, imported ledger path, optional attached HFSS session
- 출력: imported ledger result, saved `.aedt`

## Canonical state
- import-only pipeline은 active plate-stack example을 지원한다.
- save/release 순서와 imported ledger persistence를 소유한다.
- setup-ready/mesh/port/EM은 이 facade의 범위 밖이다.

## Invariants / fail-fast
- malformed ledger는 HFSS launch 전에 실패해야 한다.
- import-only path는 setup-ready helper를 호출하지 않는다.
- imported ledger write는 save 성공 후에만 수행한다.

## Collaborators
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]
- [[sdd/code/entry/import_type2_step.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 변경 시 주의점
- geometry-view import-only와 EM-ready setup path를 한 facade로 합치지 않는다.
