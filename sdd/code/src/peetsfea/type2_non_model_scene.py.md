---
title: type2_non_model_scene.py
created: 2026-04-20 @ 00:00
updated: 2026-04-20 @ 00:00
tags:
  - scene
  - non-model
---

# type2_non_model_scene.py

## Source
- Path: `src/peetsfea/type2_non_model_scene.py`
- Code note path: `sdd/code/src/peetsfea/type2_non_model_scene.py.md`
- Status: implemented
- Primary plan: [[sdd/plans/0.2.22-type2-step-scene-split]]

## 역할
- type2 non-model scene resolution과 non-model scene ledger/shape 생성을 담당한다.
- `tx_region_actual` tile derivation, `tx_region_actual_stack_space` reservation-volume derivation, and tilt transform contract를 소유한다.

## 입력 / 출력
- 입력: parsed non-model base specs, derived specs, seed, modeled RX bounds for tilt
- 출력: resolved `NonModelBoxSpec` tuple, non-model `bd.Shape` tuple, `NonModelObjectLedgerEntry`, tilt transforms

## Public API
- `TxRegionActualStackSpaceTiltTransform`
- `resolve_tx_region_actual_stack_space_tilt_enabled`
- `parent_tx_region_actual_object_id_for_stack_space_object_id`
- `is_concrete_tx_region_actual_stack_space_object_id`
- `resolve_tx_region_actual_stack_space_tilt_transform`
- `apply_tx_region_actual_stack_space_tilt_transform`
- `require_non_model_object_spec`
- `resolve_non_model_scene_specs`
- `build_non_model_scene_shapes`
- `build_non_model_scene_entry`

## Canonical state
- non-model scene member order is `environment`, `tx_region`, concrete `tx_region_actual` members, concrete `tx_region_actual_stack_space` members, `rx_region_max`.
- stack-space tilt transform is the only shared transform used by non-model reservation bodies and geometry-only TX column bodies.
- stack-space parent ids are derived from concrete stack-space object ids by exact naming rules.

## Invariants / fail-fast
- `tx_region_actual` must fit within `tx_region`.
- concrete actual-region tiles must be equal subdivisions with no gaps or overlaps.
- stack-space members must stay within owning tile Z bounds after tilt and down-shift.
- unsupported object ids, duplicate specs, invalid range counts, and missing parent specs raise immediately.

## Collaborators
- [[sdd/code/src/peetsfea/type2_scene_geometry.py]]
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- `type2_step_export.py` depends on this module for tilt transforms and concrete stack-space id handling.
- Do not add compatibility aliases back through `type2_step_scene.py` for underscore helpers.
