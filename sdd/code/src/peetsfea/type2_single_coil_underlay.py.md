---
title: type2_single_coil_underlay.py
created: 2026-04-20 @ 00:00
updated: 2026-04-20 @ 00:00
tags:
  - scene
  - underlay
---

# type2_single_coil_underlay.py

## Source
- Path: `src/peetsfea/type2_single_coil_underlay.py`
- Code note path: `sdd/code/src/peetsfea/type2_single_coil_underlay.py.md`
- Status: in-progress
- Primary plan: [[sdd/plans/0.2.22-type2-step-scene-split]]

## 단일 책임
- single-coil underlay 생성 전용 모듈.
- TX RX underlay 형상/배치 계산, 내부 페라이트 그룹 정합성, 레이블/치수 유효성 검증을 담당한다.

## 입력 / 출력
- 입력:
  - `resolve_tx_underlay_placement_descriptor`:
    - `owner_spec`: `NonModelBoxSpec`
    - `modeled_min_z`: float
    - `modeled_max_x`: float
    - `repeat_count`: int
    - `gap_mm`: float
  - `build_tx_wall_parallel_scene_shapes`: `_TxUnderlayPlacementDescriptor`
  - `build_rx_underlay_scene_shapes`:
    - `owner_spec`: `NonModelBoxSpec`
    - `repeat_count`: int
    - `modeled_bounds_min_xyz`: `Point3`
    - `modeled_bounds_max_xyz`: `Point3`
  - `single_coil_expected_ferrite_groups`:
    - `role`: `"tx_single_coil"` or `"rx_single_coil"`
    - `underlay_scene_children`: `tuple[bd.Shape, ...]`
  - `single_coil_scene_children_with_grouped_ferrite_family`:
    - `base_scene_children`: `tuple[bd.Shape, ...]`
    - `underlay_scene_children`: `tuple[bd.Shape, ...]`
    - `expected_exported_body_groups`: `tuple[ExportedBodyGroup, ...]`
- 출력:
  - `_TxUnderlayPlacementDescriptor`
  - underlay 본체 `tuple[bd.Shape, ...]`
  - `tuple[ExportedBodyGroup, ...]`
  - ferrite 그룹이 결합된 최종 장면 자식 `tuple[bd.Shape, ...]`

## Canonical state
- TX underlay floor/wall placement is derived from the owner region and modeled bounds.
- RX backing fills the available `rx_region_max` X depth behind the RX coil stack while preserving PET/PSA:ferrite:air ratio `1.5:2.0:0.2`.
- collapsed underlay body names remain exact import/export contract names.
- underlay layer thickness는 `repeat_count`와 기본 단층 두께의 곱으로 계산된다.

## Invariants / fail-fast
- repeat count와 effective layer thickness은 underlay emit 시 반드시 양수여야 한다.
- TX underlay는 owner 평면 정합성(XY), RX underlay는 owner 평면 정합성(YZ)을 엄격히 요구한다.
- RX backing 잔여 두께는 양수여야 한다.
- underlay 그룹은 underlay 본체 라벨 순서와 1:1 대응해야 한다.
- label 길이는 32자 이하만 허용된다.
- 모든 실패는 즉시 `RuntimeError`로 노출된다(폴백 없음).

## Collaborators
- [[sdd/code/src/peetsfea/type2_single_coil_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_scene_geometry.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]
- [[sdd/code/tests/type2/test_build_type2_step.py]]

## 변경 시 주의점
- Do not emit TX floor underlay bodies where current tests require omission.
- Do not weaken ferrite group ordering for single-coil underlay bodies.

## 변환 포인트
- `src/peetsfea/type2_step_scene.py`에서 underlay 블록의 순수 생성/검증 책임을 분리한다.
- `src/peetsfea/type2_single_coil_scene.py`에서 본 모듈이 제공하는 helper를 호출해 오케스트레이션만 수행한다.

## 관련 위험
- underlay body 라벨 변경 또는 순서 변경은 STEP export 그룹/재매핑과 테스트 기대값에 직접 영향.
- descriptor 기하 계산 규칙이 바뀌면 TX wall-stack 높이/깊이, RX backing 비율 오차로 회귀 가능.

## 관련 노트
- [[sdd/plans/0.2.22-type2-step-scene-split]]
