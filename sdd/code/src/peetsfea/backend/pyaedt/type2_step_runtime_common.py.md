---
title: type2_step_runtime_common.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - hfss-import
  - runtime
---

# type2_step_runtime_common.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_runtime_common.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_runtime_common.py.md`
- Related architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]
- Collaborators:
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]

## 역할
- type2 import-only/runtime setup 공통 HFSS session helper를 제공한다.
- headless HFSS session 생성, attached-session fresh-design rehome, current object-name validation을 한곳에 고정한다.

## 입력 / 출력
- 입력:
  - `design_name`
  - `HfssSession`
  - `ModelerSession`
- 출력:
  - headless `HfssSession`
  - validated current object-name lists

## Canonical state
- Module-level mutable state는 없다.
- attached-session rehome contract의 canonical owner다.

## Invariants / fail-fast
- attached import는 dirty design object set이 비어 있지 않으면 `insert_design(...)`로 fresh design을 만들고 그 design이 활성화되어야 한다.
- `design_name`, imported object names, `_raw` access는 모두 non-empty / non-null fail-fast다.

## 직접 의존
- `peetsfea.aedt.Hfss`
- `peetsfea.aedt.protocols`
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]

## 변경 시 주의점
- type2 import-only와 setup-ready path가 attached-session rehome semantics를 공유해야 한다.
- 이 helper에 mesh/boundary/port ownership을 섞지 않는다.

