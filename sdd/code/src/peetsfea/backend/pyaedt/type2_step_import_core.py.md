---
title: type2_step_import_core.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 00:45
tags:
  - hfss-import
  - core
---

# type2_step_import_core.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_core.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py.md`
- Status: active
- Related feature plan: [[sdd/plans/0.2.22-type2-tx-rx-shared-plate-stack-import-only]], [[sdd/plans/0.2.22-type2-plate-stack-sandwich-grouping]]

## 역할
- scene STEP를 HFSS에 import하고 partition/style/adapter를 조합해 imported ledger를 만든다.

## 입력 / 출력
- 입력: `HfssSession`, step ledger path, output/imported-ledger paths, validated step ledger
- 출력: `Type2ImportedLedger`

## Canonical state
- import core는 geometry-view import-only owner다.
- active plate roles도 imported ledger modeled entry로 남긴다.
- imported ledger는 export ledger contract를 유지하면서 imported object names와 recreated ferrite groups(`g_ferrite_tx`, `g_ferrite_rx`)를 추가한다.

## Invariants / fail-fast
- scene import가 새 HFSS objects를 만들지 않으면 실패한다.
- owner-fit validation과 style application이 끝난 뒤 adapter entry를 만든다.
- ferrite group recreation은 styling 직후, imported ledger merge 전에 실행한다.
- group recreation 결과 이름은 요청한 고정 group name과 일치해야 한다.
- setup-ready semantics는 여기서 실행하지 않는다.

## Collaborators
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 변경 시 주의점
- imported ledger write 책임을 setup-ready와 다시 섞지 않는다.
