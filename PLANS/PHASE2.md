# PHASE2 - DD 코일 거울대칭 생성 방식 전환 (tx_dd + rx_dd)

## 1. 목표
- DD 코일 페어를 copy/translate 방식이 아니라 mirror 대칭으로 생성한다.
- 좌우 코일 winding 방향이 반대가 되도록 하여 연결선(feed/return) 거리를 줄이고 배치 의도를 명확히 한다.

## 2. 배경 문제
- 단순 복제 배치는 형상 방향/엔드포인트 방향성이 동일해 연결선 최적화와 자기장 의도와 충돌할 수 있다.
- DD 쌍의 물리적 대칭 계약을 코드 구조로 강제할 필요가 있다.

## 3. 요구사항
- 적용 범위: tx_dd + rx_dd
- 기준 코일을 1개 생성한 뒤 mirror transform으로 반대편 코일 생성
- 좌우 winding 방향이 서로 반대가 되도록 endpoint/폴라리티 메타데이터를 정합시킨다.
- 기존 region 경계 및 배치 계약을 유지한다.

## 4. 인터페이스/구조 변경
- DD 전용 생성 헬퍼 분리:
  - build_dd_base_centerline(...)
  - mirror_centerline_about_plane(...)
  - build_dd_pair(...)
- polarity/endpoint 산출 규칙을 mirror-aware 계약으로 교체
- 그룹 메타데이터에 mirror axis 및 winding direction 기록(디버깅 가능성 강화)

## 5. 구현 계획
1. tx_dd 생성 루프를 base+mirror 방식으로 리팩터링
2. rx_dd 생성 루프도 동일 방식 적용
3. side 판정/폴라리티 계산 로직을 mirror 규칙 기반으로 업데이트
4. bbox 검증 및 region violation 검증 기존 로직과 연결
5. geometry metadata에 mirror 관련 필드 추가

## 6. 테스트
- tx_dd: selected_count=2,4 케이스
- rx_dd: selected_count=2 케이스
- 좌우 bbox 대칭성 검증
- winding 반대 방향 검증
- endpoint 근접성(연결선 길이) 검증
- 기존 seed 결정론 유지 검증

## 7. 완료 기준
- DD 쌍이 mirror 대칭 형상으로 생성된다.
- 좌우 winding 방향이 반대로 기록/검증된다.
- 기존 배치 제약(region bounds, clearance) 위반 없이 동작한다.

## Assumptions
- 실패 정책은 retry 고정 (drop/clamp 미사용)
- feasibility 제약은 활성 그룹 전체에 적용
- PHASE2는 tx_dd와 rx_dd를 같은 릴리즈 범위로 처리
