# Phase 3 - Geometry Generation on Multi-PCB with Profiled Coils

## Goal
Phase 2에서 결정된 group/pcb 선택 결과를 기반으로 다중 PCB에 코일을 독립 생성한다.
코일은 profile 기반 turn 폭/간격을 사용하고, 보드 간 연결은 여전히 구현하지 않는다.

## Preconditions
- Phase 2에서 `selected_coil_groups`, `selected_pcbs`가 manifest에 기록되어야 함.
- TX 영역 제약이 resolver에서 이미 검증되어야 함.
- 기존 연결 레이어 제거 정책(open endpoints 유지)이 계속 유효해야 함.

## In Scope
- `outer_x/outer_y` 기반 직사각 centerline 생성.
- 턴별 `trace_k/gap_k/pitch_k` 적용.
- inner margin 종료조건으로 `turn_count_used` 계산.
- 그룹 템플릿 기반 코일 인스턴싱:
  - tx_dd 2/4
  - tx_vertical 0~4 (span 등간격)
  - rx_dd 2
- PCB별 `present==1` 대상만 생성.
- board/local transform + mounts 적용.
- polarity 방향 메타데이터 출력.
- board/group/turn/profile debug 저장.

## Out of Scope
- Tx/Rx Unite 수행.
- PCB 간 전기적/기하학적 연결.
- shortest-path routing 최적화.

## Geometry Metadata Contract
- `board_debug[]`: board_id, present, transform, constraints_ok, cad_probe.
- `group_debug[]`: group_kind, instance_index, board_id, turn_count_used.
- `turn_profile_debug[]`: k별 trace/gap/pitch.
- `vertical_layout_debug[]`: tx_vertical 좌표/간격(delta).
- `polarity_debug[]`: current_direction, b_field_direction.
- naming:
  - `coil_{group}_g{idx}_b{board_idx}_{design_id}`
  - `fr4_b{board_idx}_{design_id}`

## Work Packages
1. centerline 생성기 profile 지원 버전 구현.
2. inner margin solver 구현 + fail-fast 조건 정의.
3. group별 base geometry -> instance transform 파이프라인 구현.
4. tx_vertical 등간격 배치기 구현.
5. pair spacing(tx_dd/rx_dd) 배치 반영.
6. polarity metadata 생성기 구현.
7. present board 필터링 + mounts 배치 적용.
8. debug metadata 저장 확장.
9. 콘솔 요약(활성 PCB/코일 수/제약 결과) 출력.

## Validation Rules
- 모든 세그먼트 axis-aligned.
- 모든 `trace_k`, `gap_k`, `pitch_k > 0`.
- inner margin 위반 없이 종료.
- `tx_vertical_count >= 2`이면 등간격 오차 `<= tol`.
- 총 코일 수 상한 `<= 10`.
- object naming 충돌 없음.
- polarity 계약 위반 시 실패.

## Test Matrix
- profile bias 변화 시 turn 분포 변화.
- inner_margin 증가 시 `turn_count_used` 감소 확인.
- tx_vertical count 경계: `0,1,2,4`.
- span 경계: `0`, `15`.
- tx_dd 모드: `2`, `4`.
- optional PCB off/on에서 mount 반영 검증.

## Exit Criteria
- 그룹 기반 다중 코일이 다중 PCB에 결정론적으로 생성됨.
- profile/inner_margin/vertical span 결과가 metadata에 완전 기록됨.
- optional PCB 선택 변화가 seed 기반으로 재현 가능.

## Risks and Rollback
- 리스크: solver 종료 조건 오류로 self-overlap 혹은 under-generation.
- 대응: 턴별 bbox/간격 검증 + 즉시 예외.
- 롤백: profile 모드를 임시 uniform으로 제한해 안정화.
