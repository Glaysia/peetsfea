---
title: type2_step_import_ledger.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 10:41
tags:
  - type2
  - hfss-import
  - aedt
---

# type2_step_import_ledger.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_ledger.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py.md`
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]
- Parent note: [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 역할
- type2 STEP ledger file load + required-field validation을 담당한다.
- non-model/member ownership lookup helper와 canonical bounds reader를 제공한다.
- modeled/non-model id uniqueness, placement owner uniqueness preflight를 fail-fast로 고정한다.

## 입력 / 출력
- 입력: step ledger path
- 출력:
  - `ValidatedStepLedger`
  - owner/member lookup helpers
  - outer-bounds reader helpers
  - validated AEDT object name reader

## Canonical state
- canonical import metadata source는 export ledger다.
- `scene_step_path`는 파일 존재 검증을 통과한 절대 경로로 canonicalized 된다.

## Invariants / fail-fast
- `scene_step_path` must exist.
- modeled/non-model sections must be non-empty and satisfy required-key contract.
- modeled `placement_owner_id`는 non-model member object에서 exact-one로 resolve되어야 한다.
- duplicate object id와 duplicate member id는 hard failure다.

## 직접 의존
- `peetsfea.aedt.failfast.validate_aedt_name`
- `peetsfea.aedt.protocols` 없음; pure ledger validation layer로 유지한다.

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 변경 시 주의점
- AEDT runtime ops를 이 파일에 넣지 않는다.
- adapter merge logic를 ledger validation과 섞지 않는다.
