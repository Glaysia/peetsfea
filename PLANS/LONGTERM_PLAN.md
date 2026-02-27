# LONGTERM Plan

## 목적
- `PLANS/LONGTERM_PLAN.md`를 장기 전략의 단일 SSOT 문서로 사용한다.
- `peetsfea`는 spec-first/결정론/재현성 중심의 설계-생성 엔진에 집중한다.
- 대규모 분산 실행과 오케스트레이션은 분리 프로젝트(`peetsfea-runner`)로 유지한다.

## 장기 비전
- 동일한 설계 계약(TOML + seed)으로 여러 형상군(type1, type2, ...)을 안정적으로 생성한다.
- Geometry/EM/Validation 계약을 타입 독립 인터페이스로 고정해 신규 타입 온보딩 비용을 줄인다.
- 생성 결과는 재현 가능한 중간 산출물(설계 파일/manifest/repro 입력) 중심으로 관리한다.

## 고정 제약
- Rx 패키지 물리 제약은 벽면 정렬/적층 순서/두께 예산 계약을 우선한다.
- Tx-Rx 거리 제약(예: 110mm)과 같은 시스템 제약은 장기적으로도 preflight 단계에서 우선 검증한다.
- Headless AEDT, deterministic sampling, 명시적 기본값 정책을 유지한다.

## 타입 확장 로드맵
1. Type1 안정화
- 현재 파이프라인의 계약(선택/형상/EM/검증)을 문서와 테스트로 고정한다.
- 숨은 파생/이름 드리프트를 제거한다.

2. Type2 온보딩
- Type1과 동일한 공용 계약(`em_ready_objects`, `em_endpoints`, `em_context`)을 만족하도록 어댑터를 추가한다.
- 타입 전용 형상 생성 로직만 분리하고 공용 단계는 재사용한다.

3. TypeN 확장
- 타입별 차이를 입력 계약/어댑터 레이어로 국소화한다.
- 공용 테스트 스위트(결정론/재현/validation gate)를 모든 타입에 동일 적용한다.

## Foundation Model/전이 전략
- 형상별 원시 파라미터를 직접 학습하지 않고 Physics IR(Topology + 무차원 특징 + 근사 EM priors)로 정규화한다.
- Shared trunk + domain adapter 구조로 신규 형상군 전이 비용을 낮춘다.
- Multi-fidelity(근사식/저해상도 HFSS/고해상도 HFSS)와 active learning 루프를 결합한다.
- 모델 릴리즈는 HFSS 검증 게이트를 통과한 버전에만 허용한다.

## 실행/운영 리스크
- 라이선스/원격 환경 차이: 머신별 AEDT/SSH/Slurm 편차로 실패 가능.
- 결정론 드리프트: 숨은 랜덤 소스, 버전 차이, 암묵 파생식에서 재현성 손상 가능.
- 고동시성 장애: 500+ 동시 작업에서 타임아웃/프로세스 유실/모니터 병목 가능.
- 장시간 해석 중단: hang 프로세스 누적 시 클린업 및 재시도 정책 부재 위험.

## 리스크 대응 원칙
- stage별 timeout과 heartbeat를 표준화한다.
- 실패 산출물과 로그를 구조화해 재시도/원인분석 루프를 자동화한다.
- spec/docs/code 테스트를 동시에 갱신하는 문서-코드 동기화 규칙을 강제한다.
- 지원/비지원 기능을 preflight에서 명시적으로 분리해 조기 실패시킨다.

## 의존성 및 선행조건
- Python 3.12 + Pyaedt + AEDT 실행 환경.
- 타입 확장 전에 Type1의 계약과 회귀 테스트가 안정 상태여야 한다.
- 문서 버전과 실행 버전(`spec_version`, manifest 계약)은 항상 동기화한다.
- 장기 ML/전이 단계는 데이터 스키마/IR 스키마 버전 관리가 선행되어야 한다.

## 운영 기본값
- spec-first + deterministic by default.
- TOML은 설계 정의만 담당하고, 실행 토폴로지/머신 설정은 Python 코드에서 관리한다.
- 하위호환은 자동 보정보다 명시적 버전 실패를 우선한다.
