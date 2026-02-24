# PHASE3 Master Plan - HFSS Operation Pipeline

## 1. DD 간격 비율화 정책 (공통 헤더)
- DD 코일 간격은 더 이상 mm 절대값이 아니라, 해당 배치 영역 Y축 길이에 대한 비율로 정의한다.
- 신규 파라미터:
  - `coil_spacing.tx_dd_pair_spacing_ratio`
  - `coil_spacing.rx_dd_pair_spacing_ratio`
- 계산식:
  - `tx_dd_pair_spacing_mm = tx_dd_pair_spacing_ratio * tx_region_outer_h_mm`
  - `rx_dd_pair_spacing_mm = rx_dd_pair_spacing_ratio * rx_region_outer_h_mm`
- 유효 범위(초안): `0.0 <= ratio <= 0.1`, count 25정도
- Backward policy: PHASE3 적용 시 mm 경로는 deprecated가 아니라 제거(명시적 오류).

## 2. PHASE3 전체 목표
- geometry 생성 이후 실제 HFSS 오퍼레이션을 완성한다.
- 범위: 그룹화, 직렬연결 브리지, TX/RX unite, FR4 subtract, radiation, lumped port, analysis setup, result 템플릿, 최종 validation.

## 3. 서브 문서 맵
- `PHASE3A_GEOMETRY_AND_CONNECTIVITY.md`: 오브젝트 그룹화, 직렬연결, unite, subtract
- `PHASE3B_EM_SETUP_BOUNDARY_AND_PORTS.md`: radiation, 경계, TX/RX lumped port
- `PHASE3C_RESULTS_AND_ANALYSIS_SETUP.md`: 해석 setup/sweep, 결과 템플릿
- `PHASE3D_VALIDATION_GATE_AND_ACCEPTANCE.md`: validation gate, 테스트, 수용 기준

## 4. 인터페이스 변경 요약
- `SelectedParameters` 변경:
  - 제거: `tx_dd_pair_spacing_mm`, `rx_dd_pair_spacing_mm`(직접 입력 의미)
  - 추가: `tx_dd_pair_spacing_ratio`, `rx_dd_pair_spacing_ratio`
  - 파생: 내부에서 mm spacing 계산
- TOML path 변경:
  - `coil_spacing.tx_dd_pair_spacing_ratio`
  - `coil_spacing.rx_dd_pair_spacing_ratio`
- 제약식 변경:
  - ratio 범위 제약 추가
  - 기존 spacing(mm) 제약식은 ratio 기반 식으로 대체

## 5. 마이그레이션/호환성 정책
- PHASE3 시점부터 기존 mm spacing 경로는 명시적 오류로 처리한다.
- 스펙 버전과 README/예제 TOML을 동기화한다.
- 변환 스크립트는 선택사항으로 분리하고 본 작업의 완료 조건에는 포함하지 않는다.

## 6. 완료 정의 (Definition of Done)
- PHASE3A~3D에 정의된 항목이 모두 구현 계획으로 결정완료 상태여야 한다.
- 문서 간 파라미터명/수식/검증 규칙이 완전히 일치해야 한다.
- 테스트 축(파생식/연결성/subtract/포트/setup/결과/validation hard fail)이 모든 문서에 반영되어야 한다.
