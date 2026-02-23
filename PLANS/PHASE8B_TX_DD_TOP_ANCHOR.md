# Phase 8-B - TX DD 상단 부착 Anchor

## Goal
TX DD 코일을 PCB 기준이 아닌 `tx_region_dd` 상단면 기준으로 배치해, DD 영역 내부 상단 부착 계약을 강제한다.

## Summary
- TX DD 코일 z anchor를 scene 영역 계산과 일치시킴
- `tx_dd_top_clearance_mm` 적용
- 영역 상단에서 아래로 clearance 적용

## In Scope
- `src/peetsfea/backend/pyaedt/geometry/square_spiral.py`
- metadata/디버그 필드(필요 시)
- `tests/test_coil_geometry_runner.py`

## Formula
- `z_anchor = tx_dd_origin_z + tx_dd_z - tx_dd_top_clearance_mm - coil_thickness_ref`
- `coil_thickness_ref`는 코일 z extents/단면 정의와 일관된 기준 사용

## Implementation Steps
1. scene 생성과 동일한 `tx_dd_origin_z`, `tx_dd_z` 재사용 경로 구성
2. TX DD에만 상단 anchor 적용
3. tx_vertical/rx_dd 기존 경로는 이 단계에서 유지

## Testing
- TX DD 코일 bbox 상단이 DD 영역 상단면에서 clearance만큼 떨어지는지
- clearance=0 경계 케이스 통과
- clearance>dd_z 위반은 제약 또는 geometry fail-fast

## Exit Criteria
- TX DD 코일이 DD 영역 상단 부착 규칙 충족
