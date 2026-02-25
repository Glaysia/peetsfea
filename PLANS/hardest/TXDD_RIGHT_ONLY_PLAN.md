# TxDD 우측 Endpoint 우선 반영 계획 (1층/2층 분기)

## 요약
- 현재 코드 기준 `tx_dd.selected_count`는 2(1층) 또는 4(2층)만 허용한다.
- 이번 단계는 `tx_dd` 우측(right) 경로 규칙만 반영한다.
- `tx_vertical`, `tx_dd` 좌측, `rx_dd`, 리드/유나이트는 제외한다.

## 목표 규칙
1. `tx_dd` 2개(1층): 우측 라벨 `C -> d`
2. `tx_dd` 4개(2층): 우측 하층/상층 라벨 `C -> a`(아래), `a -> D`(위)
3. 우측 대상 전류 방향은 모두 `ccw`
4. 비대상은 기존 동작 유지

## 구현 범위
- `GroupEndpointEntry`에 `start_label`, `end_label` 추가
- 코일 생성 시 기본 라벨(`A -> a`) 기록
- 우측 `tx_dd` 인스턴스만 후처리로 라벨/전류 방향 덮어쓰기
- 테스트/README 동기화

## 구현 상세
### 1) 타입 (`src/peetsfea/types/manifest.py`)
- `TerminalLabel = Literal["A","B","C","D","a","b","c","d"]` 추가
- `GroupEndpointEntry`에 `start_label`, `end_label` 추가

### 2) 지오메트리 (`src/peetsfea/backend/pyaedt/geometry/square_spiral.py`)
- endpoint 기록 시 기본 라벨 저장:
  - `start_label="A"`
  - `end_label="a"`
- helper `_apply_txdd_right_endpoint_rule(group_endpoints, coil_polarity)` 추가
- 로직:
  - `group_kind == "tx_dd"` and `instance_side == "right"` 후보 수집
  - 각 후보의 `z_center=(start_z+end_z)/2` 계산
  - 후보 수 1개: `C -> d`, `current_direction=ccw`
  - 후보 수 2개: `z_center` 오름차순 정렬 후
    - index 0(하층): `C -> a`, `ccw`
    - index 1(상층): `a -> D`, `ccw`
  - tie-break: `(z_center, board_id, group_instance_index)`
  - 후보 수 3개 이상은 계약 위반 예외
- 호출 위치: 코일 생성 완료 후 metadata/em 조립 직전

### 3) 문서 (`README.md`)
- TxDD 우측-only 단계 계약 섹션 추가
- 적용/제외 범위와 1층/2층 규칙 명시

## 테스트
### 기존 회귀
- 기존 geometry/em pipeline 테스트 통과 유지

### 신규 케이스
1. `selected_count=2`, 우측 라벨 `C->d`, `ccw`
2. `selected_count=4`, 우측 하층/상층 라벨 `C->a`/`a->D`, 둘 다 `ccw`
3. 좌측 `tx_dd`는 기본 라벨(`A->a`)과 기존 전류 방향(`cw`) 유지

## 수용 기준
1. 우측 1층/2층 라벨이 규칙과 일치
2. 우측 대상 전류 방향이 항상 `ccw`
3. 비대상 범위 회귀 없음
4. 타입 검사 및 테스트 통과
