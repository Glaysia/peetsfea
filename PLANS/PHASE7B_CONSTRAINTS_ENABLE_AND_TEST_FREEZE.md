# Phase 7-B - Constraints Enabled=True 전환 및 테스트 고정

## Goal
스테이징된 제약식(`enabled=false`)을 활성화하여 런타임 preflight 계약을 완성하고, 실패/성공 케이스 테스트를 고정한다.

## Summary
- `examples/type1.toml`의 신규 제약식 `enabled=true`
- path/message 정합성 점검
- 제약 실패 시 메시지 포맷 고정

## In Scope
- `examples/type1.toml` (및 symlink된 `run/type1.toml`)
- `src/peetsfea/spec/resolver.py` 제약 파서/평가기
- `tests/test_run_manifest.py`

## Out of Scope
- geometry 좌표/평면 변경
- connection builder 구현

## Constraint Set (활성화 대상)
1. 재료/전기:
   - `via_diameter_mm > 0`
   - `pcb_thickness_mm > 0`
   - `cu_thickness_mm > 0`
   - `fr4_er > 1.0`
2. scene anchor:
   - `shelf_height_mm > 0`
   - `shelf_min_size_x_mm > 0`
   - `rx_region_bottom_from_tv_mm >= 0`
3. placement:
   - `tx_dd_top_clearance_mm >= 0`
   - `rx_face_clearance_mm >= 0`
   - `tx_dd_top_clearance_mm <= tx_region_dd_z_mm`
   - `rx_face_clearance_mm <= rx_region_thickness_mm`

## Implementation Steps
1. TOML의 해당 rule `enabled`를 true로 변경
2. resolver path 해석에 없는 키가 없는지 확인
3. 제약 실패 메시지 스냅샷 테스트 추가/갱신
4. 경계값 테스트 추가 (`==` 허용 케이스)

## Testing
- 정상: 기본 `type1.toml` 통과
- 실패: 각 신규 제약 위반 1건씩
- 회귀: 기존 제약식(`outer`, `leftover`, `total_coils`) 영향 없음

## Exit Criteria
- 신규 제약식 모두 활성
- 실패 메시지와 위반 rule id가 테스트로 고정
