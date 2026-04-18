---
title: type2_step_import_style.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 23:40
tags:
  - hfss-import
  - styling
---

# type2_step_import_style.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_style.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py.md`
- Status: active
- Related feature plans: [[sdd/plans/0.2.22-type2-rx-plate-stack-striped-copper]], [[sdd/plans/0.2.22-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- imported modeled/non-model objects의 material, color, transparency, model-state를 적용한다.

## 입력 / 출력
- 입력: modeler session, validated modeled entry, imported object names
- 출력: final imported object names list, optional reconstructed port-sheet names

## Canonical state
- plate roles도 ferrite/PET_PSA/vacuum styling과 PCB/copper styling을 받는다.
- `stack_*`, legacy underlay family는 모두 같은 ferrite/PET_PSA/vacuum styling path를 쓴다.
- port-sheet reconstruction은 coil roles와 plate-stack roles 모두 수행할 수 있다.
- plate-stack roles는 `tx_plate_port_sheet`, `rx_plate_port_sheet` 이름의 metadata-only reconstructed sheet를 추가한다.

## Invariants / fail-fast
- active plate role placement validation은 TX `min_x` anchor와 RX `min_x` anchor를 role-aware로 검사해야 한다.
- plate roles는 `owner.max_y + 5.0 mm` overhang만 허용하고 나머지 owner-fit anchor는 유지해야 한다.
- imported object styling은 exact-name partition 결과만 사용한다.

## Collaborators
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 변경 시 주의점
- active plate role styling을 single-coil assumptions에 맞춰 copper 1장 계약으로 축소하면 안 된다.
- import-only material setup는 stack/underlay ferrite family 존재 여부만을 precondition으로 삼는다.
- plate-stack reconstructed sheet 이름 drift는 imported_object_names regression과 같이 갱신해야 한다.
