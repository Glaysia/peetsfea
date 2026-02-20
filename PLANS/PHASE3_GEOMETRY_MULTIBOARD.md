# Phase 3 - Geometry Generation for 3 Coil Groups on Multi-PCB

## Goal
선택된 그룹/PCB를 기준으로 N개 PCB에 코일을 독립 생성한다. 가변 turn profile + inner margin solver를 적용하며, 보드 간 연결은 구현하지 않는다.

## In Scope
- `outer_x/outer_y` 기반 직사각 centerline 생성
- 턴별 `trace_k/gap_k/pitch_k` 계산 적용
- inner margin 종료조건 적용
- 그룹 템플릿 기반 코일 인스턴싱
  - tx_dd 2 또는 4개
  - tx_vertical 0~4개 (등간격 span 배치)
  - rx_dd 2개
- 코일 방향 메타데이터 출력
- PCB별 `present==1`만 생성
- board/local transform + mount 적용
- board/group debug 출력 저장

## Out of Scope
- Tx/Rx Unite 수행
- PCB 간 전기적/기하학적 연결
- connection routing 최적화

## Spec/Type Changes
- geometry debug 확장
  - `board_debug[]`: board id, constraint status, cad probe
  - `group_debug[]`: group kind, instance index, turn_count_used
  - `turn_profile_debug[]`: k별 trace/gap/pitch
  - `vertical_layout_debug[]`: tx_vertical 등간격 좌표와 delta
  - `polarity_debug[]`: 코일별 current/b-field 방향
- naming 규칙
  - `coil_{group}_g{idx}_b{board_idx}_{design_id}`
  - `fr4_b{board_idx}_{design_id}`

## Implementation Steps
1. centerline 생성기를 profile 기반으로 교체한다.
2. inner margin solver로 실제 `turn_count_used`를 결정한다.
3. group별 base geometry를 만들고 instance transform을 적용한다.
4. tx_vertical은 `tx_vertical_span_mm` 기반 등간격 배치한다.
5. tx_dd/rx_dd pair spacing을 배치에 반영한다.
6. 코일별 전류/자기장 방향 계약을 metadata에 기록한다.
7. PCB별 mount 규칙대로 geometry를 배치한다.
8. present=0 PCB는 skip한다.
9. 생성 객체를 group/board별로 metadata에 기록한다.
10. 콘솔에 요약(활성 PCB 수, 코일 수, constraint 결과)을 출력한다.

## Validation Rules
- 모든 세그먼트 axis-aligned
- 모든 `trace_k`, `gap_k`, `pitch_k > 0`
- inner margin 위반 없이 turn 종료
- `tx_vertical_count >= 2`이면 등간격 오차 `<= tol`
- 코일 수 상한 `<= 10`
- object naming 충돌 없음
- 방향 계약 위반 시 실패

## Test Cases
- profile bias 변화 시 turn 분포 변화 확인
- inner_margin이 큰 경우 turn_count_used 감소 확인
- tx_vertical=0,1,2,4 경계 케이스 검증
- `span=0`, `span=15` 경계 검증
- tx_dd=2/4 모드 검증
- 8 PCB(항상 4 + optional 4)에서 optional off 시 mount skip 확인

## Exit Criteria
- 그룹 기반 다중 코일이 다중 PCB에 안정적으로 생성된다.
- turn profile/inner margin/vertical span 결과가 debug에 완전 기록된다.
- optional PCB off/on에 따른 생성 결과가 결정론적으로 일치한다.

## Risks and Rollback
- 리스크: solver 종료 조건 오류로 self-overlap 또는 과소 생성
- 대응: 턴별 bbox/간격 검증 및 실패 시 즉시 예외
- 롤백: profile 모드를 임시 uniform으로 제한해 안정화 가능
