---
title: type2_single_coil_scene.py
created: 2026-04-20 @ 00:00
updated: 2026-04-20 @ 11:45
tags:
  - scene
  - single-coil
---

# type2_single_coil_scene.py

## Source
- Path: `src/peetsfea/type2_single_coil_scene.py`
- Code note path: `sdd/code/src/peetsfea/type2_single_coil_scene.py.md`
- Status: implemented
- Primary plan: [[sdd/plans/0.2.22-type2-step-scene-split]]

## 역할
- type2 single-coil modeled scene orchestration을 담당한다.
- placement offset, `tx_rect_void` bridge, transformed box specs, ferrite grouping, underlay integration, canonical coordinates, and final `ModeledObjectSceneData`를 소유한다.

## 입력 / 출력
- 입력: `ModeledSingleCoilSpec`, owner `NonModelBoxSpec`, seed
- 출력: scene child `bd.Shape` tuple and `ModeledObjectSceneData`

## 책임 경계(현재 구현)
- 이 모듈은 단일 코일 scene orchestration을 `type2_step_scene.py`에서 복사 이전한 구현으로 유지한다.
- underlay/ferrite grouping은 [[sdd/code/src/peetsfea/type2_single_coil_underlay.py]] 공개 함수를 직접 사용한다.
- port/terminal 및 일반 scene geometry helper는 계획된 `type2_single_coil_ports.py`, `type2_scene_geometry.py`가 아직 미존재인 상태라 현재 모듈 내부 helper로 유지한다.

## Canonical state
- single-coil placement consumes spec-resolved outer dimensions and owner bounds.
- transformed boxes are the canonical source for modeled bounds and terminal metadata.
- single-coil ferrite families are grouped into `g_ferrite_tx` or `g_ferrite_rx` in family creation order.

## Invariants / fail-fast
- owner plane and role plane must match.
- modeled bounds must stay within owner bounds.
- body names must be unique.
- active plate-stack roles must not call this module.

## Collaborators
- [[sdd/code/src/peetsfea/type2_single_coil_ports.py]]
- [[sdd/code/src/peetsfea/type2_single_coil_underlay.py]]
- [[sdd/code/src/peetsfea/type2_scene_geometry.py]]
- [[sdd/code/src/peetsfea/tx_rect_void.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- Preserve direct `build_modeled_single_coil_scene_data` behavior for callers importing through `type2_step_scene.py`.
- Do not add fallback placement or alternate terminal metadata paths.
