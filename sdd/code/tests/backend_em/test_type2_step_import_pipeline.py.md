---
title: test_type2_step_import_pipeline.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 10:41
tags:
  - type2
  - hfss-import
---

# test_type2_step_import_pipeline.py

## Source
- Path: `tests/backend_em/test_type2_step_import_pipeline.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_step_import_pipeline.py.md`
- Related plan: [[sdd/plans/0.2.22-type2-import-ledger-pipeline]]
- Tested source:
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py]]

## 역할
- Type2 STEP import+ledger runtime을 AEDT launch 없이 fake HFSS session으로 검증한다.
- Canonical single scene STEP를 한 번만 import하고 ownership partition이 deterministic하게 이루어지는지 검증한다.

## 입력 / 출력
- 입력:
  - test-local STEP placeholder files
  - test-local type2 STEP ledger JSON
  - fake modeler/desktop/HFSS sessions
- 출력:
  - runtime return ledger
  - written imported ledger JSON
  - fake call histories

## Canonical state
- Test-local fake modeler owns import call order, object name batches, and model-state call history.
- Test-local fake object refs own color, transparency, and material mutation history.
- The written imported ledger JSON must match runtime result.
- fake ledger fixtures use the rebased type2 scene baseline where `tx_region.bottom == 0`; the import path must consume those exported coordinates as-is.

## Invariants / fail-fast
- Canonical scene STEP import는 정확히 한 번 일어나야 한다.
- Non-model objects are assigned `model=False`; modeled objects are assigned `model=True`.
- Non-model imported objects are colored gray and made transparent after import.
- Attached-session helper path도 same normalization contract를 공유해야 한다.
- Imported TX/RX bodies are not moved; export-ledger bounds must already satisfy each role's placement-owner contract before import, including the rebased global scene Z baseline.
- Modeled ownership is resolved only by exact exported body labels; generic `SOLID*` fallback은 허용되지 않는다.
- TX multilayer exact-name sets (`tx_pcb_l{n}` + `tx_copper_stack`) are accepted and styled without collapsing back to a 2-body assumption.
- Missing scene STEP path and malformed ledger fail before HFSS launch when possible.
- Duplicate object id, missing placement owner member, missing modeled body name, missing non-model member name, unclaimed imported name, bad modeled placement, empty import diff, duplicate imported names, import `False`, and save `False` all raise.
- Headless helper path는 release `[(True, True)]`, attached-session helper path는 detach release `[(False, False)]`를 기대한다.
- Attached-session helper path도 import/save 실패 후 detach release를 시도해야 한다.

## 직접 의존
- `pytest`
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py]]

## 이 파일을 쓰는 곳
- Default pure-Python test suite.

## 관련 테스트
- This file is the direct test coverage for the split type2 STEP import runtime modules.

## 변경 시 주의점
- Do not introduce real AEDT launch here.
- If imported ledger schema changes, fake ledger builders and assertions must change together.
