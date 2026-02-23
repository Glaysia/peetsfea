# Phase 8-A - DD 오프셋 축 전환 (XZ 대칭)

## Goal
DD 코일(`tx_dd`, `rx_dd`)의 pair spacing 축을 X에서 Y로 전환해 XZ 평면(y=0) 대칭 계약을 강제한다.

## Summary
- `_coil_instance_offset()`에서 DD 오프셋을 `(dx,0,0)` -> `(0,dy,0)` 전환
- `_instance_side()` 분류 기준을 `offset.x` -> `offset.y`로 전환
- polarity/right-left 계약을 새 side 기준으로 유지

## In Scope
- `src/peetsfea/backend/pyaedt/geometry/square_spiral.py`
- `tests/test_coil_geometry_runner.py`

## Out of Scope
- RX 수직 배치
- TX/RX 면 부착 anchor

## Implementation Steps
1. DD 오프셋 로직 수정:
   - center 기준 `((idx-center)*spacing)`를 y에 적용
2. side 판정 업데이트:
   - y<0: left, y>0: right
3. polarity 메타데이터 회귀 확인

## Testing
- DD 두 코일 생성 시 y 부호가 반대인지 확인
- x는 동일 기준점 유지 확인
- coil_polarity의 left/right 대응 유지 확인

## Exit Criteria
- DD 배치가 XZ 거울대칭으로 동작
- 기존 count/spacing 결정론 유지
