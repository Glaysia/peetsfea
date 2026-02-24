# PHASE8 - Analysis Setup + Result 템플릿

## 목표
- 해석 설정과 기본 결과 세트를 자동 생성한다.
- setup/sweep/result 생성을 공용 EM 파이프라인(`analysis` 단계)으로 이전한다.

## 범위
- Setup:
  - `Setup_6p78MHz` @ `6.78MHz`
- Sweep:
  - `Sweep_1to42MHz` (`1MHz ~ 42MHz`, interpolation)
- 결과 템플릿:
  - `S(1,1)`, `S(2,2)`, `S(2,1)`
  - `Z(1,1)`, `Z(2,2)`, `Z(2,1)`
  - coupling 지표 템플릿(`k_est`, `M_est`)
- 메타데이터:
  - `analysis_setup`, `post_templates`
  - `repro_mode` (`sampled_toml`, `frozen_toml`, `manifest_json`)
- 사전 검증:
  - 결과 템플릿 생성 전 입력 계약(그룹별 outer 매핑/selection 하드체크 결과) 검증
  - replay(`sampled_toml`, `frozen_toml`, `manifest_json`)에서 동일 단계 재실행 보장

## 완료 기준
- setup/sweep/result 템플릿 존재성 검증 가능
- type1/type2 모두 동일 공용 단계 호출로 setup/result 생성 가능
