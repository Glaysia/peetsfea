---
title: type2_step_import_style.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 21:45
tags:
  - hfss-import
  - styling
---

# type2_step_import_style.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_style.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py.md`
- Status: active
- Related feature plan: [[sdd/plans/0.2.25-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- imported modeled/non-model objects의 material, color, transparency, model-state를 적용한다.

## 입력 / 출력
- 입력: modeler session, validated modeled entry, imported object names
- 출력: final imported object names list, optional reconstructed port-sheet names

## Canonical state
- plate roles도 ferrite/PET_PSA/vacuum styling과 PCB/copper styling을 받는다.
- port-sheet reconstruction은 coil roles만 수행한다.
- `terminal_metadata.kind == "none"` plate role은 sheet reconstruction 없이 imported names 그대로 반환한다.

## Invariants / fail-fast
- active plate role placement validation은 TX `min_x` anchor와 RX `min_x` anchor를 role-aware로 검사해야 한다.
- plate roles에 port-sheet vertices를 요구하면 안 된다.
- imported object styling은 exact-name partition 결과만 사용한다.

## Collaborators
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 변경 시 주의점
- active plate role styling을 single-coil assumptions에 맞춰 copper 1장 계약으로 축소하면 안 된다.
