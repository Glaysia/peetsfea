# IPT Foundation Model and Transfer Strategy

## Priority and Timing
본 문서는 **아주 먼 미래 로드맵**이다.

- 전제 조건: `type1` 스펙/파이프라인이 먼저 완성되고 안정화되어야 한다.
- 적용 시점: `type1` 완료 직후가 아니라, 운영/검증이 충분히 끝난 뒤의 후속 단계로 다룬다.
- 현재 우선순위: 본 문서 구현보다 `type1` 완성과 결정론/검증 체계 고도화를 우선한다.

## Goal
HFSS(Maxwell) 기반 IPT 해석에서 형상이 크게 달라져도 기존 학습 자산을 재사용해 다음을 개선한다.

- 신규 형상 적응 속도 (학습 샘플 수, 수렴 반복)
- 최종 정확도 (`k`, `Q`, 효율, 손실 추정)
- 해석 가능성 (왜 성능이 변했는지 원인 추적)

핵심 아이디어는 "형상별 입력 파라미터"를 직접 학습하지 않고, 물리적으로 의미 있는 중간 표현으로 변환한 뒤 공통 모델을 학습하는 것이다.

## LLVM Analogy Applied to IPT
LLVM 비유를 IPT에 대응하면 아래와 같다.

- Frontend: 형상/재료/배치 스펙 -> 공통 중간 물리 표현(Physics IR)
- Midend: Physics IR 기반 공통 사전학습 + 물리 제약 학습
- Backend: 형상군별 소규모 어댑터(head)로 `k`, `Q`, 손실, 효율 예측

즉, "형상별 파라미터 공간"은 Frontend에서 흡수하고, Midend는 형상 불변 물리구조를 학습하며, Backend는 도메인별 미세 보정만 수행한다.

## Physics IR (Intermediate Representation) Contract
IR은 형상이 달라도 동일 스키마를 유지해야 한다.

### 1) Topology Graph
- 노드: 코일/페라이트/도체판/차폐/공기영역
- 엣지: 인접, 자기결합 가능 경로, 전기적 연결 관계
- 전역 속성: 주파수, 거리, 정렬 오프셋, 권선 방향 규약

### 2) Dimensionless Features
스케일 변화에 강한 무차원 지표를 우선 사용한다.

- 정규화 거리(`gap / coil_diameter`)
- 정규화 권선 피치(`pitch / trace_width`)
- 형상비(`aspect ratio`)
- 상대 투자율 대비 공진 주파수/손실 관련 지표

### 3) Coarse EM Priors
정확 해석값이 아니라도 빠르게 구할 수 있는 근사 물리량을 포함한다.

- 근사 상호인덕턴스 `M_hat`
- 근사 누설 인덕턴스/저항 `L_leak_hat`, `R_hat`
- 근사 자기장 커버리지/집중도 지표

## Model Architecture
### A. Shared Trunk + Domain Adapters
- Trunk: 그래프/집합 기반 인코더(GNN or Set Transformer)
- Adapter: 형상군별 소형 모듈(LoRA/adapter/head)
- Output heads: `k`, `Q_tx`, `Q_rx`, 효율, 손실분해(동손/와전류손)

### B. Physics-Constrained Training
데이터 오차 + 물리 제약 잔차를 동시 최적화한다.

- `L_total = L_data + lambda_phys * L_phys + lambda_cons * L_consistency`
- `L_phys` 예시:
  - 수동소자/에너지 보존 위배 패널티
  - 결합계수 범위 제약 (`0 <= k <= 1`)
  - 기본적인 공진/임피던스 관계 위배 패널티
- `L_consistency` 예시:
  - 동일 IR에서 대칭 변환(미러/회전) 시 예측 일관성

### C. Multi-Fidelity Learning
고비용 HFSS 데이터만으로는 확장성이 낮다. 저비용 근사 데이터와 결합한다.

- Fidelity-0: 해석적/근사식 빠른 샘플
- Fidelity-1: 축소 메쉬 HFSS
- Fidelity-2: 고정밀 HFSS
- 학습 시 fidelity-aware loss 또는 teacher-student distillation 적용

## Data and Label Strategy
### 1) Canonical Task Set
형상이 달라도 공통으로 예측할 타깃을 고정한다.

- `k(f)` curve 요약 지표(peak, bandwidth)
- `Q_tx`, `Q_rx`
- 효율/손실(조건별)
- 제약 위반 여부(발열, stray field 등)

### 2) Meta-Condition Tokens
도메인 조건을 토큰으로 명시해 전이 성능을 높인다.

- 형상군 ID (DD, solenoid, planar spiral, etc.)
- 소재군 ID
- 동작 영역 (주파수/거리 class)

### 3) Active Learning Loop
불확실성이 큰 케이스에 HFSS 계산 예산을 우선 배정한다.

- 불확실성 추정(ensemble or MC dropout)
- 상위 불확실 샘플 재해석
- 재학습 주기 자동화

## Transfer Learning Scenarios
### 1) Same physics, new geometry family
- Shared trunk freeze, adapter/head만 우선 학습
- 성능 부족 시 trunk 일부만 점진 해제

### 2) New material regime
- material embedding + 일부 trunk 재학습
- 기존 geometry adapter 재사용

### 3) New operating range (freq/distance)
- 조건 토큰 확장 + calibration head 추가
- 기존 모델의 불확실성 기준으로 재학습 범위 결정

## Interpretability by Design
사후 분석을 위해 "설명 가능한 경로"를 모델에 내장한다.

- 개념 병목(concept bottleneck):
  - 중간 노드에서 `M_hat`, `L_hat`, `R_hat`, stray index 예측
  - 최종 `k`, `Q`, 손실은 이 중간 개념을 사용
- 민감도 보고:
  - IR feature에 대한 gradient/SHAP 기반 영향도
- 실패 원인 분해:
  - "형상 요인 vs 소재 요인 vs 배치 요인" 점수화

## Execution Roadmap (Pragmatic)
### Phase 1: IR 정의 및 데이터 파이프라인
- TOML spec -> Physics IR 변환기 구현
- 기존 HFSS run manifest와 IR 동기화 저장
- 결정론 계약: `same spec + same seed => same IR`

### Phase 2: Baseline Foundation Trunk
- 단일 형상군으로 trunk pretrain
- 물리 제약 loss 최소 세트 적용
- 기준선 대비 성능/재현성 측정

### Phase 3: Adapter-based Transfer
- 신규 형상군을 adapter만으로 빠르게 적응
- full fine-tuning 대비 데이터 효율 비교

### Phase 4: Multi-fidelity + Active Learning
- 저비용 샘플 + 고정밀 HFSS 혼합
- 불확실성 기반 재해석 루프 구축

### Phase 5: Production Contract
- 모델 버전/IR 버전/seed 고정
- HFSS 검증 게이트 통과 시에만 배포
- 실패 케이스 자동 수집 및 재학습 큐 등록

## KPIs (Must Track)
- 전이 성능: 신규 형상군에서 required HFSS samples
- 정확도: `k`, `Q`, 손실 MAE/MAPE
- 보정 비용: adapter-only vs full fine-tune 학습시간
- 신뢰성: 제약 위반률, out-of-distribution 탐지율
- 해석성: 원인분해 리포트 일관성(전문가 리뷰)

## Risks and Mitigations
- 리스크: IR 정의가 부실하면 전이가 실패
  - 대응: 무차원 지표 + topology graph를 최소 핵심으로 고정
- 리스크: 물리 loss 과적용으로 data fit 저하
  - 대응: `lambda_phys` 스케줄링 및 ablation 표준화
- 리스크: HFSS 라벨 노이즈/설정 편차
  - 대응: solver 설정 메타데이터를 입력 토큰으로 포함
- 리스크: 형상군 편향 데이터셋
  - 대응: 형상군별 균형 샘플링 + active learning

## Immediate Next Actions
1. `run/` 산출물에 Physics IR JSON 저장 필드 추가
2. `k`, `Q`, 손실 타깃 정의를 고정한 baseline dataset schema 작성
3. trunk+adapter 최소 모델 PoC를 단일 형상군에서 먼저 검증
