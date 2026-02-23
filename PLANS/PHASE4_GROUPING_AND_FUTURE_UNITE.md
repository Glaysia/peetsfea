# Phase 4 - Metadata Lock for Future Unite and Serial Linking

## Goal
Phase 3 생성 결과를 기반으로, Tx/Rx Unite 및 PCB 간 serial link 구현에 필요한 메타데이터 계약을 고정한다.
이 단계는 구현 단계가 아니라 계약 고정 단계다.

## Preconditions
- Phase 3에서 group/board별 객체 생성과 polarity metadata가 기록되어야 함.
- open endpoint 정책이 유지되어야 함(실제 연결 객체는 아직 없음).

## In Scope
- group role별 copper object 분류 규약 고정.
- group/instance endpoint 저장 규약 고정.
- coil polarity 저장 규약 고정.
- future Unite 입력 계약 고정.
- future shortest-link 입력/출력 계약 고정.

## Out of Scope
- `modeler.unite` 실제 수행.
- connection polyline 실제 생성.
- 전기적 시뮬레이션 검증.

## Metadata Contract
- `group_objects = {tx_dd:[], tx_vertical:[], rx_dd:[]}`
- `unite_groups = {tx:[], rx:[]}`
- `group_endpoints[]`
- `coil_polarity[]`
- `GroupEndpointEntry`:
  - `group_kind`, `group_instance_index`, `board_id`
  - `start_xyz`, `end_xyz`
  - `present`
- `CoilPolaritySpec`:
  - `group_kind`, `instance_side`, `current_direction`, `b_field_direction`
- future job fields:
  - `unite_by_role: bool`
  - `serial_link_strategy: "shortest_euclidean"`
  - `serial_link_pairs` (future output)

## Work Packages
1. Phase 3 산출물에서 group별 copper object name 집계기 구현.
2. role 매핑 규칙 고정:
   - tx role: tx_dd + tx_vertical
   - rx role: rx_dd
3. 코일 인스턴스 start/end 월드좌표 endpoint 저장.
4. 코일 인스턴스 polarity 저장.
5. Unite 입력 객체 정렬 순서 규칙 고정(이름 정렬).
6. shortest-link tie-breaker 규칙 고정(사전순).
7. future 연결 단계 polarity 보존 검증 규칙 고정.

## Validation Rules
- `unite_groups.tx/rx`는 present=true 객체만 포함.
- present coil instance마다 endpoint 2개 정확히 존재.
- endpoint는 transform 반영 월드좌표.
- role 분류와 group kind 일치.
- polarity와 그룹/좌우 인스턴스 계약 일치.

## Test Matrix
- mixed tx/rx + optional off 케이스 grouping 정확성.
- endpoint 개수/좌표 유효성.
- polarity 매핑 정확성.
- shortest-link tie-breaker 결정론.
- metadata만으로 Unite 입력 재구성 가능성.

## Exit Criteria
- 구현자가 metadata만 보고 Tx/Rx Unite 구현 가능.
- 구현자가 metadata만 보고 shortest serial link 구현 가능.
- 그룹/역할/endpoint/polarity 계약에 추가 의사결정이 남지 않음.

## Risks and Rollback
- 리스크: endpoint 정의 변경 시 하위 단계 재작업 비용 증가.
- 대응: endpoint 정의를 centerline index(start=0, end=-1) 기준으로 고정.
- 롤백: endpoint 보강 필드(예: edge midpoint) 임시 추가.
