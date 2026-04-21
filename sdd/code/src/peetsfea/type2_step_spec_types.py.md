---
title: type2_step_spec_types.py
created: 2026-04-21 @ 20:35
updated: 2026-04-22 @ 00:35
tags:
  - step-export
  - spec
---

# type2_step_spec_types.py

## Source
- Path: `src/peetsfea/type2_step_spec_types.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_spec_types.py.md`
- Status: active
- Related feature plans: [[sdd/plans/0.2.22-type2-step-spec-shared-types-split]]

## 역할
- active type2 step spec의 shared type layer를 소유한다.
- shared top-level constants, `Point3`, `Literal` aliases, `TypedDict`s, dataclasses through `Type2StepSpec`, and role/object/plane helpers를 한 군데로 모은다.

## 입력 / 출력
- 입력: 없음. parser and downstream type2 modules가 import하는 shared type definitions.
- 출력: `RangeSpec`, type2 object spec dataclasses, constraint typed dicts, step spec container, and role helper functions.

## Canonical state
- type2 parser/import/export code는 shared spec shape를 이 module에서만 바라본다.
- `tx_single_coil`, `rx_single_coil`, `tx_rect_void_columns`, `tx_plate_stack`, `rx_plate_stack` role mappings are canonical here.
- `tx_region`, `rx_region_max`, `XY`, and `YZ` resolution rules are centralized here and must stay aligned with the parser facade.
- `ModeledTxRectVoidColumnsSpec` is the only modeled-columns dataclass; no extra alias is owned here.
- `ModeledTxRectVoidColumnsSpec` owns one turn-count range field, `equivalent_turn_count`; its canonical active sweep range is `[false, 0.1111111111111111, 31.0, 100]`, and legacy `series_total_turn_count` and `parallel_total_turn_count` fields are not part of the active dataclass.

## Invariants / fail-fast
- unsupported modeled roles raise immediately.
- helper functions do not provide fallback resolution paths.
- shared type aliases and dataclasses must remain importable without importing the parser module.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]
- [[sdd/code/src/peetsfea/type2_sampled.py]]
- [[sdd/code/src/peetsfea/type2_non_model_scene.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]
- [[sdd/code/tests/type2/test_sample_type2_entry.py]]
- [[sdd/code/tests/type2/test_type2_tx_plate_stack_array_export.py]]

## 변경 시 주의점
- parser behavior stays in the facade module; this file only owns shared type ownership and role resolution helpers.
- keep the import surface stable for older callers that still import these names through `peetsfea.type2_step_spec`.
