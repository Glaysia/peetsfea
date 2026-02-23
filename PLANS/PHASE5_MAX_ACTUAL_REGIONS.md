# Phase 5 - Max/Actual Region Dual Generation

## Goal
TX/RX 논모델 영역을 코일과 독립적으로 항상 2종(`max`, `actual`) 생성해,
후속 제약(코일 내부 배치 강제)의 기준 경계를 고정한다.

## Summary
- 생성 대상:
  - `tx_region_max` + 내부 2분할(`tx_region_vertical`, `tx_region_dd`) + 하단 leftover
  - `rx_region_max`, `rx_region_actual`
- 기준:
  - `actual`: seed 기반 selected 값
  - `max`: TOML `range`의 `end` 값
- 좌표 규약:
  - wall: ZY 평면 접촉, `-X` 방향
  - tv: ZY 평면 접촉, `+X` 방향
  - rx region: ZY 평면 접촉, `+X` 방향
  - rx bottom z = `tv.base_z_mm + 1.0`

## In Scope
- resolver에 `selected_parameters_max` 계산 추가(`range end` 사용).
- manifest에 `selected_parameters_max` 저장.
- geometry에서 TX/RX max+actual 박스 동시 생성.
- scene metadata kind 확장(`tx_region_vertical/dd/empty`, `rx_region_max/actual`).
- RX 두께 TOML 고정값 적용(4mm).

## Out of Scope
- 코일을 영역 내부로 강제하는 검증/클램프.
- 코일 회전/배치 재설계.
- 전기적 연결(유나이트/직렬 링크).

## Interface Changes
- `Manifest`:
  - `selected_parameters_max` 필드 추가.
- `GeometryMetadata.scene_objects[].kind`:
  - 기존 + `tx_region_max`, `tx_region_actual`, `rx_region_max`, `rx_region_actual`.
- resolver API:
  - max 선택값 동시 반환 버전 도입.

## Geometry Rules
1. Wall
- `origin_x = -wall_thickness_mm`
- size는 `(wall_t, wall_y, wall_z)`

2. TV
- `origin_x = 0`
- size는 `(tv_t, tv_w, tv_h)`

3. RX (max/actual 공통 anchor)
- `origin_x = 0`
- `origin_z = tv_base_z_mm + 1.0`
- plane `YZ`
- 두께축은 `+X`

4. TX (max/actual 공통 anchor)
- 코일과 무관한 고정 anchor 사용
- TV 아래 배치 정책 유지

## Validation
- 모든 scene 박스는 non-model.
- `actual`이 `max` 내부에 포함되는지 축별 검증.
- 치수 <= 0 fail-fast.

## Tests
- manifest 테스트:
  - `selected_parameters_max` 존재/결정론 확인.
  - seed 변경 시 max 불변.
- geometry 테스트:
  - scene kind 7개 확인.
  - wall/tv/rx의 X방향 규약 확인.
  - rx bottom = `tv.base_z + 1` 확인.
  - non-model 생성 확인.

## Exit Criteria
- max/actual 경계가 metadata로 완전 재현 가능.
- 코일 정보 없이도 영역 배치가 결정됨.
- `ruff`, `mypy`, `pytest` 통과.
