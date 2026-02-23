# Phase 7-A - Resolver Path/Type Wiring

## Goal
TOML에 추가된 고정 설계값(`coil_material.*`, `scene_anchor.*`, `coil_placement.*`)을 resolver가 실제로 읽어 `selected_parameters`로 연결한다.

## Summary
- `SCALAR_RANGE_SPECS`에 신규 수치 path 추가
- 문자열 계약(`dd_mirror_plane`, `rx_plane`) 파서 추가
- `FIXED_DEFAULTS` 의존 제거
- Manifest 타입과 resolver 선택 결과를 1:1로 잠금

## In Scope
- `src/peetsfea/spec/resolver.py`
- `src/peetsfea/types/manifest.py`
- `tests/test_run_manifest.py`, `tests/test_hashing.py`, `tests/test_coil_geometry_runner.py`

## Out of Scope
- 코일 실제 배치 로직 변경
- `constraints.enabled` 전환
- 연결기/운영 자동화

## Interface Changes
- `SelectedParameters` 신규 필드:
  - `shelf_height_mm`
  - `shelf_min_size_x_mm`
  - `rx_region_bottom_from_tv_mm`
  - `tx_dd_top_clearance_mm`
  - `rx_face_clearance_mm`
  - `dd_mirror_plane`
  - `rx_plane`
- 기존 하드코딩 필드(`via_diameter`, `pcb_thickness`, `cu_thickness`, `fr4_er`)를 TOML 입력으로 전환

## Implementation Steps
1. `SCALAR_RANGE_SPECS` 확장:
   - `coil_material.via_diameter_mm -> via_diameter`
   - `coil_material.pcb_thickness_mm -> pcb_thickness`
   - `coil_material.cu_thickness_mm -> cu_thickness`
   - `coil_material.fr4_er -> fr4_er`
   - `scene_anchor.shelf_height_mm -> shelf_height_mm`
   - `scene_anchor.shelf_min_size_x_mm -> shelf_min_size_x_mm`
   - `scene_anchor.rx_region_bottom_from_tv_mm -> rx_region_bottom_from_tv_mm`
   - `coil_placement.tx_dd_top_clearance_mm -> tx_dd_top_clearance_mm`
   - `coil_placement.rx_face_clearance_mm -> rx_face_clearance_mm`
2. 문자열 파서 함수 추가:
   - `coil_placement.dd_mirror_plane.value`는 `"XZ"`만 허용
   - `coil_placement.rx_plane.value`는 `"YZ"`만 허용
3. `FIXED_DEFAULTS` 제거 후 `selected` 주입을 TOML 값으로 대체
4. 테스트 픽스처 TOML 생성기에 신규 섹션 추가

## Validation
- 누락 path는 fail-fast (`Missing required path`)
- 문자열 enum 위반 시 명확한 에러
- 동일 spec+seed 재현성 유지

## Exit Criteria
- 신규 TOML 필드 전부 `selected_parameters`에 반영
- 하드코딩 기본값 제거 완료
- 타입/테스트 통과
