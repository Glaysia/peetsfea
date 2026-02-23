# Phase 8-C - RX YZ 수직 배치 및 +X Face Anchor

## Goal
RX DD 코일을 바닥 수직(YZ 평면)으로 생성하고, `rx_region_actual`의 TV측(+X 최대 면)에 부착한다.

## Summary
- RX 전용 YZ centerline 생성 함수 추가
- +X face anchor 계산에 `rx_face_clearance_mm` 반영
- 기존 XY 경로와 분리해 TX/RX 배치 규칙 충돌 방지

## In Scope
- `src/peetsfea/backend/pyaedt/geometry/square_spiral.py`
- `tests/test_coil_geometry_runner.py`

## Formula
- `x_anchor = rx_origin_x + rx_t_max - rx_face_clearance_mm - coil_thickness_ref`
- YZ plane에서 코일 외곽이 `rx_region_actual` y/z 범위를 넘지 않아야 함

## Implementation Steps
1. YZ 스파이럴 포인트 생성 함수 도입
2. RX DD 객체 생성 시 YZ 함수 경로 사용
3. RX 전용 anchor/translation 로직 분리

## Testing
- RX 코일 모든 점 x가 거의 일정(평면성)
- RX 코일이 +X 면 근접(anchor) 확인
- rx_face_clearance 경계값 테스트

## Exit Criteria
- RX DD 코일이 반드시 YZ 수직 배치
- TV측 +X face 부착 규칙 충족
