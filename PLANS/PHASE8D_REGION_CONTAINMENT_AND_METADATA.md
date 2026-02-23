# Phase 8-D - 영역 포함성 검사 및 메타데이터 확장

## Goal
TX/RX 코일이 지정 영역(`tx_region_dd`, `rx_region_actual`) 내부인지 축별로 검사하고 결과를 metadata에 남긴다.

## Summary
- axis-aligned bbox 포함성 검사 도입
- 위반 시 fail-fast + overflow 리포트
- debug metadata 확장(`in_region_ok`, `violations`)

## In Scope
- `src/peetsfea/backend/pyaedt/geometry/square_spiral.py`
- `src/peetsfea/types/manifest.py`
- `tests/test_coil_geometry_runner.py`

## Violation Schema
- `object_name`
- `region_kind`
- `axis` (`x|y|z`)
- `overflow_mm`

## Implementation Steps
1. region bbox 추출 유틸 구현
2. coil bbox vs region bbox 포함성 계산
3. 위반 목록 누적 후 정책 적용:
   - 기본: 위반 1건 이상이면 RuntimeError
4. metadata/debug에 판정 결과 저장

## Testing
- 정상: violations 빈 배열, `in_region_ok=true`
- 실패: x/y/z 초과 각각 1케이스
- 허용오차 경계(tol) 케이스

## Exit Criteria
- 영역 포함성 결과가 metadata로 재현 가능
- 위반 시 원인 축/초과량 확인 가능
