---
title: import_type2_step.py
created: 2026-04-19 @ 21:42
updated: 2026-04-19 @ 21:42
tags:
  - entry
  - import-only
  - hfss
---

# import_type2_step.py

## Source
- Path: `entry/import_type2_step.py`
- Code note path: `sdd/code/entry/import_type2_step.py.md`
- Status: planned active
- Related feature plan: [[sdd/plans/0.2.25-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- active type2 geometry를 import-only로 AEDT에 여는 entrypoint다.
- plate-stack active example을 setup-ready가 아니라 import pipeline으로 보내는 human/agent 실행 경로를 제공한다.

## 입력 / 출력
- 입력: type2 STEP ledger path, optional output/imported-ledger paths
- 출력: imported `.aedt`, imported ledger JSON

## Canonical state
- geometry-view 목적의 canonical runtime은 `type2_step_import_pipeline`이다.
- active TX/RX plate-stack example은 이 entry를 통해 AEDT에서 시각 확인한다.

## Invariants / fail-fast
- setup-ready로 자동 우회하지 않는다.
- ledger가 missing/malformed이면 HFSS launch 전에 실패해야 한다.
- import-only contract를 넘어 mesh/port/EM 단계로 진행하지 않는다.

## Collaborators
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]
- [[sdd/code/entry/build.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 변경 시 주의점
- geometry-view entry를 build/setup-ready entry와 섞지 않는다.
