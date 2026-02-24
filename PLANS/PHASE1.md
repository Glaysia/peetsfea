# PHASE1 - 생성 가능성 제약 강화 (Selection 단계 차단)

## 1. 목표
- Geometry 빌드 단계에서 발생하던 "코일이 영역에 물리적으로 들어가지 않는 오류"를 Selection 단계에서 선제 차단한다.
- 생성 불가능 조합은 실패 처리 후 retry로 넘겨, 최종적으로 "생성 가능한 manifest만" 후속 단계로 전달한다.

## 2. 배경 문제
- 현재 constraints는 selected parameters 중심 검증만 수행한다.
- group geometry(turn_count_max, trace, gap) + 실제 배치 가능 영역(tx_region_vertical_z_mm 등)의 결합 조건이 빠져 있다.
- 결과적으로 preflight 통과 후 geometry 단계에서 런타임 실패가 발생한다.

## 3. 요구사항
- 활성 그룹(selected_count > 0)에 대해 최소 1턴 생성 가능성을 제약으로 강제한다.
- tx_vertical은 available_outer_y = min(outer_y, tx_region_vertical_z_mm) 기준으로 평가한다.
- tx_dd, rx_dd도 동일 정책으로 평가한다.
- 실패 시 SelectionConstraintError를 발생시키고 기존 retry 루프를 사용한다.

## 4. 인터페이스 변경
- constraints DSL 확장:
  - feasible_turns(group_kind, outer_x_path, outer_y_path, outer_cap_y_path)
  - active_group(group_kind)
- resolver 제약 평가 함수 시그니처 확장:
  - selected_group_geometry, selected_coil_groups를 함께 받도록 변경

## 5. 구현 계획
1. selected_group_geometry path resolver 추가
2. DSL 파서에 feasible_turns/active_group 추가
3. _evaluate_constraints에서 활성 그룹 조건부 평가 적용
4. run/type1.toml에 feasibility 규칙 추가
5. 실패 메시지에 디버깅 값(kind, trace, gap, available dims, feasible_turns) 포함

## 6. 테스트
- 재현 seed(예: 10)에서 attempt=0 제약 실패 검증
- retry attempt 증가 시 유효 조합 선택 검증
- selected_count=0인 그룹은 feasibility skip 검증
- DSL 인자/경로 오류 케이스 검증
- 결정론 보장: 동일 (toml, seed, attempt) -> 동일 결과

## 7. 완료 기준
- geometry 단계에서 "cannot fit in region" 유형 오류가 selection 단계에서 선차단된다.
- run 파이프라인은 retry를 통해 유효 manifest를 생성한다.
- 관련 단위 테스트와 회귀 테스트가 통과한다.
