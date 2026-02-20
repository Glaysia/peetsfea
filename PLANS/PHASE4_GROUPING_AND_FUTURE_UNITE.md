# Phase 4 - Group Metadata Lock for Future Unite and Serial Linking

## Goal
현재 생성 결과를 기반으로 Tx/Rx Unite 및 PCB 간 직렬 연결(최단거리) 구현을 위한 메타데이터 계약을 확정한다. 이 페이즈에서는 계약/검증만 고정하고 실제 Unite/연결은 구현하지 않는다.

## In Scope
- group role별 copper object 분류 규약 확정
- group/instance endpoint 저장 규약 확정
- coil polarity 계약 저장 규약 확정
- future Unite 입력 계약 고정
- future 최단거리 연결 입력/출력 계약 고정

## Out of Scope
- 실제 `modeler.unite` 수행
- 실제 connection polyline 생성
- 시뮬레이션 전기적 검증

## Spec/Type Changes
- `GeometryMetadata` 추가
  - `group_objects = {tx_dd:[], tx_vertical:[], rx_dd:[]}`
  - `unite_groups = {tx:[], rx:[]}`
  - `group_endpoints[]`
  - `coil_polarity[]`
- `GroupEndpointEntry`
  - `group_kind`, `group_instance_index`, `board_id`
  - `start_xyz`, `end_xyz`
  - `present`
- `CoilPolaritySpec`
  - `group_kind`, `instance_side`, `current_direction`, `b_field_direction`
- future job contract
  - `unite_by_role: bool`
  - `serial_link_strategy: "shortest_euclidean"`
  - `serial_link_pairs` (future output)

## Implementation Steps
1. Phase 3 결과에서 group별 copper object name을 집계한다.
2. role 매핑 규칙을 고정한다.
   - tx role: tx_dd + tx_vertical
   - rx role: rx_dd
3. 각 코일 인스턴스의 start/end 월드좌표를 endpoint로 저장한다.
4. 각 코일 인스턴스의 polarity를 `CoilPolaritySpec`으로 저장한다.
5. 미래 Unite 순서를 이름 정렬 기준으로 고정한다.
6. 미래 최단거리 연결 tie-breaker를 사전순 규칙으로 고정한다.
7. future 연결 단계에서 polarity 보존 검증을 의무화한다.

## Validation Rules
- `unite_groups.tx/rx`에는 present=true 객체만 포함
- endpoint는 모든 present coil 인스턴스에 대해 정확히 2개
- endpoint 좌표는 transform 반영된 월드좌표
- role 분류가 group kind와 일치
- polarity가 그룹/좌우 인스턴스 규약과 일치

## Test Cases
- mixed tx/rx + optional off 케이스에서 grouping 정확성 확인
- endpoint 개수 및 좌표 유효성 확인
- polarity 매핑 정확성 확인
- future shortest-link tie-breaker 결정론 테스트
- metadata만으로 Unite 입력 재구성 가능 여부 확인

## Exit Criteria
- 다음 구현자가 metadata만 보고 Tx/Rx Unite 구현 가능
- 다음 구현자가 metadata만 보고 최단거리 직렬 연결 구현 가능
- 그룹/역할/endpoint/polarity 계약에 추가 의사결정이 남지 않음

## Risks and Rollback
- 리스크: endpoint 정의 변경 시 하위 단계 대규모 재작업
- 대응: endpoint 정의를 centerline index (start=0, end=-1)로 고정
- 롤백: endpoint 보강 필드(예: edge midpoint)를 임시 추가 가능
