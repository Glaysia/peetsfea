# PHASE6 - FR4 Subtract와 3D 모델 유효성

## 목표
- FR4에서 구리를 subtract(tool 보존)하고 모델 유효성을 점검한다.
- 해당 단계를 type1 내부 구현이 아니라 공용 EM 파이프라인 단계로 이전한다.

## 범위
- 각 FR4 blank에 대해 TX/RX united copper subtract
- 설정: tool 객체 유지
- 체크:
  - subtract 후 FR4 유효 volume
  - 비정상 중첩/오류 객체 여부
- validation 로그:
  - 치수/제약 출처 TOML path를 함께 기록
  - `no_hidden_derivation_passed` 체크 결과 연계
  - 공용 로그 포맷 고정: `path`, `object`, `stage`

## 완료 기준
- subtract 파이프라인이 안정적으로 완료됨
- 실패 시 객체명/원인 포함 hard fail 메시지 제공
- type2 geometry에서도 동일 subtract/validation 단계 재사용 가능
