# Long-Term Wireless TV WPT Plan

## Mission and Fixed Constraints
본 문서는 Wireless TV 적용을 위한 장기 설계 제약을 고정한다.

- Tx와 Rx는 각각 허용 직육면체(envelope) 범위 내에서만 존재한다.
- Tx-Rx 최소 표면 거리 제약은 항상 `110.0 mm`로 고정한다.
- Rx 측 물리 적층 순서는 고정한다.
  - 앞면 -> 벽 방향: `TV 알루미늄판 -> Rx PCB들 -> 페라이트판 -> 벽`
- Rx는 벽 평행면 기준으로 배치한다.
- Rx 패키지 전체 두께 제약은 `<= 4.0 mm`로 고정한다.

## Coordinate Frame and Envelope Contract
좌표계는 벽 정렬 좌표계를 사용한다.

- `[scene]`
  - `frame = "wall_aligned"`
  - `parallel_plane_lock = true`
  - `tx_rx_surface_min_distance_mm = 110.0`
- `[envelope.tx]`
  - `x_range`, `y_range`, `z_range`
- `[envelope.rx]`
  - `x_range`, `y_range`, `z_range`
  - `max_total_thickness_mm = 4.0`
  - `pcb_thickness_mm = 1.6`

거리 검증 규약:
- `min_surface_distance(tx_envelope, rx_envelope) = 110.0 mm ± tol`
- `rx_envelope`는 Rx stack 전체(`tv_al_sheet + rx_pcbs + rx_ferrite_plate`)를 포함해야 한다.

## Coil Group Contract and Variable Profiles
코일 그룹은 다음을 고정한다.

- `tx_dd` : 2 또는 4개 (동일 코일, 두겹 배치 허용)
- `tx_vertical` : 0~4개 (동일 코일, 등간격 배치)
- `rx_dd` : 2개 고정 (동일 코일)
- 총 코일 수 상한: `<= 10`

가변 형상/배치 파라미터:
- `outer_x`, `outer_y`
- `turn_count_max`
- `inner_margin_x`, `inner_margin_y`
- `trace_profile` (biased_linear)
- `gap_profile` (biased_linear)
- `tx_dd_count_mode` (`2 | 4`)
- `tx_dd_pair_spacing_mm`
- `tx_vertical_count`
- `tx_vertical_span_mm` (`0.0 ~ 15.0`)
- `rx_dd_pair_spacing_mm`

턴별 계산 규약:
- `trace_k = f_trace(k, n)`
- `gap_k = f_gap(k, n)`
- `pitch_k = trace_k + gap_k`

수직코일 등간격 규약:
- `n = tx_vertical_count`
- `n <= 1`이면 내부 간격 계산 생략
- `n >= 2`이면 `delta = tx_vertical_span_mm / (n - 1)`
- 모든 수직코일 중심은 PCB 두께축 기준 등간격

## Coil Current/Field Direction Contract
관찰자 기준(“TV를 정면으로 보는 사람” 기준축)으로 전류/자기장 규약을 고정한다.

- Tx DD 오른쪽 코일: 전류 반시계(CCW), 자기장 위 방향
- Tx DD 왼쪽 코일: 위 코일과 반대 극성, 자기장 아래 방향
- Tx Vertical 코일: 자기장 오른쪽 방향이 되도록 전류 방향 고정
- Rx DD 오른쪽 코일: 전류 시계(CW), 자기장 들어가는 방향
- Rx DD 왼쪽 코일: 전류 반시계(CCW), 자기장 나오는 방향

## RX Stack Contract (TV-Side)
Rx 적층은 순서/재료/두께 제약을 명시적으로 고정한다.

- `rx_stack.layer_order = ["tv_al_sheet", "rx_pcbs", "rx_ferrite_plate", "wall"]`
- 순서 위반 시 preflight 실패

재료 기본값:
- `[materials.rx_ferrite]`
  - `enabled = false`
  - `mu_r = 300.0`
  - `model = "linear_isotropic"`
- `[materials.rx_al_sheet]`
  - `enabled = false`
  - `position = "front_of_rx_pcbs"`

두께 예산식:
- `rx_total_thickness = t_al + t_pcb_max + t_ferrite + t_bond + t_clearance`
- 제약: `rx_total_thickness <= 4.0 mm`
- 기본 PCB 두께 기준: `t_pcb_max = 1.6 mm`

## Connection Architecture Roadmap
현재 연결부는 제거하고, 이후 연결기를 분리 구현한다.

- Phase 0에서 기존 폐루프/레이어 연결부를 제거
- 모든 코일은 open terminal endpoint를 갖는 독립 객체로 생성
- endpoint metadata를 저장해 후속 연결기 입력으로 사용
- 미래 연결기 규약
  - role/group 기반 Unite
  - shortest-path-with-clearance 링크 생성
  - 연결 시 코일 극성 계약 보존 검증

## Material Roadmap (Ferrite and Aluminum)
Phase gate 기반으로 소재를 점진 적용한다.

- Phase 5에서 Rx ferrite + TV aluminum 동시 활성화 A/B 테스트
- Ferrite 전략 가정:
  - 일반적으로 ferrite는 누설자속을 줄여 k를 올리는 방향으로 작용
  - 본 구조에서는 `Tx 하부 + Rx 후면` 동시 적용이 k에 유리할 가능성이 가장 높음
- DOE 실험 팩터:
  - ferrite 위치: `none / tx_only / rx_only / both`
  - ferrite `mu_r`: 기본 300 (향후 sweep 가능)
  - aluminum on/off 및 두께
  - 110mm 거리 고정 상태에서 k 비교

## Multi-Domain Considerations Checklist
장기 계획 수립 시 아래 영역을 동시에 점검한다.

- Geometry: 간섭, 여유 간격, self-overlap, endpoint 일관성
- EM: coupling, 누설자계, detuning, 알루미늄 영향
- Mechanical: 벽면 설치 공차, TV 후면 공간, 조립 편차
- Thermal: Tx hotspot, ferrite/al sheet 열영향
- Manufacturing: PCB/판재 공차, 고정 구조, 반복 조립 신뢰성
- Safety/Compliance: EMC, stray field, 절연 거리
- Data/Experiment: seed 결정론, 실패 케이스 로깅, 커버리지
- Software: spec backward compatibility, hash 안정성, debug observability

## Phase Milestones and Exit Gates
- Phase 0 (Connection Reset)
  - 기존 연결부 제거, endpoint만 유지
- Phase 1 (Spec Remodel)
  - `rx_stack`/`mu_r=300`/110mm 거리 계약 반영
- Phase 2 (Resolver/Manifest)
  - profile + group + presence 결정론 확립
- Phase 3 (Geometry)
  - 그룹 기반 코일 생성, envelope/거리 검증
- Phase 4 (Grouping Contract)
  - future Unite/링크 입력 메타데이터 잠금
- Phase 5 (Material Integration)
  - Rx ferrite + TV aluminum 활성화 A/B
- Phase 6 (Connection Builder)
  - 적층 순서 유지 상태에서 Unite/연결 구현

Exit gate 핵심:
- 110mm 거리 + stack 제약 동시 만족
- Rx 4.0mm 두께 예산 위반 0건
- total_coils(`tx_dd + tx_vertical + rx_dd`) <= 10
- 동일 spec+seed 재현성 보장

## Verification Strategy
1. stack 순서 정상/역순 입력 검증
2. ferrite `mu_r=300` 기본값 적용 검증
3. thickness budget 경계값 검증 (`3.99`, `4.00`, `4.01 mm`)
4. 110mm 거리 + stack 제약 동시 검증
5. 코일 수 경계 검증 `(4,4,2)=10 허용`, `(4,5,2)=실패`
6. 수직코일 등간격 검증 (`n=0,1,2,4`, `span=0`, `span=15`)
7. seed 고정 재현성 검증

## Risks and Mitigations
- 리스크: stack 모델 누락으로 기구 제약 불일치
  - 대응: `layer_order` 강제 검증
- 리스크: 소재 모델 단순화로 초기 성능 오차
  - 대응: Phase 5에서 A/B 비교 및 보정
- 리스크: 연결기 늦은 도입으로 구조 변경 비용 증가
  - 대응: endpoint/net contract를 Phase 0~4에서 선고정
- 리스크: 극성 계약 불일치로 상쇄 자계 발생
  - 대응: polarity metadata + preflight polarity check 추가

## Assumptions and Defaults
- Rx는 벽과 평행한 평면 배치
- TV 알루미늄판은 Rx PCB 전면(벽 반대 방향)
- 페라이트 기본 투자율은 `mu_r=300`
- Rx 총 두께 제약은 `<=4.0 mm`
- Tx-Rx 최소 표면 거리 제약은 항상 `110 mm`
- Ferrite는 우선 `tx+rx 동시 적용`이 k에 유리하다는 가설로 시작
