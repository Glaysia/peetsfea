---
title: type2_scene_geometry.py
created: 2026-04-20 @ 00:00
updated: 2026-04-20 @ 00:00
tags:
  - scene
  - geometry
---

# type2_scene_geometry.py

## Source
- Path: `src/peetsfea/type2_scene_geometry.py`
- Code note path: `sdd/code/src/peetsfea/type2_scene_geometry.py.md`
- Status: implemented
- Primary plan: [[sdd/plans/0.2.22-type2-step-scene-split]]

## 역할
- type2 scene/export code가 공유하는 Build123d geometry helper를 담당한다.
- shape bounds를 `CanonicalCoordinates` payload로 변환하고, labeled solid/group construction helper를 제공한다.

## 입력 / 출력
- 입력: `bd.Shape`, `NonModelBoxSpec`, label + origin/size tuple
- 출력: `CanonicalCoordinates`, labeled `bd.Shape`

## Public API
- `canonical_from_shape`
- `canonical_from_non_model_box`
- `canonical_from_non_model_specs`
- `build_non_model_box_shape`
- `build_labeled_solid_box`
- `build_labeled_group`

## Canonical state
- canonical coordinate extraction은 shape bounding box에서만 파생한다.
- label preservation은 caller-owned exact-name contract를 유지한다.

## Invariants / fail-fast
- helper는 fallback geometry를 만들지 않는다.
- zero/negative geometry는 caller responsibility에서 검증하고, helper가 검출 가능한 invalid state는 raise한다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_non_model_scene.py]]
- [[sdd/code/src/peetsfea/type2_single_coil_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- exact label contract를 약화하지 않는다.
- `type2_step_scene.py`를 역참조하지 않는다.
