---
title: type2_step_import_style.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 15:45
tags:
  - hfss-import
  - styling
---

# type2_step_import_style.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_style.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py.md`
- Status: active

## Ownership
- Primary plan: [[sdd/plans/0.2.22-type2-plate-stack-material-merge]]
- TX array plan: [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]]
- Primary architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- imported modeled/non-model objects의 material, color, transparency, model-state를 적용한다.

## 입력 / 출력
- 입력: modeler session, validated modeled entry, imported object names
- 출력: final imported object names list, optional reconstructed port-sheet names

## Canonical state
- plate roles도 ferrite/PET_PSA/vacuum styling과 PCB/copper styling을 받는다.
- active plate-stack ferrite-family는 merged exact names(`tx_stack_pet_psa|tx_stack_ferrite|tx_stack_air`, `rx_stack_pet_psa|rx_stack_ferrite|rx_stack_air`)로만 ferrite/PET_PSA/vacuum styling path를 탄다.
- TX array branch-local ferrite/PET/air bodies are styled by material family while remaining under one `tx_plate_stack` entry.
- TX array connector sheet conductors may expose no AEDT material property after `cover_lines`; their conductor identity
  comes from exact TX conductor membership and model-state, while branch copper solids must still expose material state.
- TX array owner-fit validation keeps the TX max-Z top-aligned contract but allows X overflow for rotated copied branches.
- legacy underlay/wall prefixes는 single-coil import path에서만 same-material styling path를 유지한다.
- port-sheet reconstruction은 coil roles와 plate-stack roles 모두 수행할 수 있다.
- plate-stack roles는 `tx_plate_port_sheet`, `rx_plate_port_sheet` 이름의 metadata-only reconstructed sheet를 추가한다.
- TX array reconstructs one shared `tx_plate_port_sheet` from parallel bus terminal metadata.
- plate-stack Y placement validation follows the exported active window contract:
  `outer_bounds_size_y - 5.0 mm` is the active Y span, active bounds are centered on global `Y=0`,
  and the `-Y` stub overhang starts from active `min_y`, not owner `min_y`.

## Invariants / fail-fast
- active plate role placement validation은 single-branch TX `min_x` anchor와 RX `min_x` anchor를 role-aware로 검사해야 한다.
- TX array entries with branch-local `tx_b{i}_...` names may exceed `tx_region` X bounds after copied-branch rotation; this is not a placement failure.
- plate roles는 active centered Y window 내부 배치와 active `min_y - 5.0 mm` overhang만 허용하고,
  full owner-Y footprint 강제나 owner `min_y - 5.0 mm` anchor로 되돌아가면 안 된다.
- imported object styling은 exact-name partition 결과만 사용한다.
- copper styling must keep branch solids and connector sheets under the same exact-name conductor family; only exact
  `tx_array_*_sheet_s*` connector sheets may be material-property-free, and all other copper names must expose material state.
- plate-stack ferrite-family material preflight(`ensure_underlay_materials`)는 merged exact-name contract만 인식하고 legacy `*_stack_*_uN` fallback을 두지 않는다.
- plate-stack Z validation은 `z_usage_ratio`로 줄어든 active window를 허용하되 TX는 owner max-Z에, RX는 owner min-Z에 role-aware anchor를 유지해야 한다.
- Single-branch and TX array mode both keep owner max-Z validation, and TX array mode must still reject Z overflow.

## Collaborators
- [[sdd/code/src/peetsfea/type2_plate_stack.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 변경 시 주의점
- active plate role styling을 single-coil assumptions에 맞춰 copper 1장 계약으로 축소하면 안 된다.
- import-only material setup는 stack/underlay ferrite family 존재 여부만을 precondition으로 삼는다.
- plate-stack reconstructed sheet 이름 drift는 imported_object_names regression과 같이 갱신해야 한다.
