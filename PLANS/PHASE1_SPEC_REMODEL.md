# Phase 1 - Spec Remodel for Grouped Coils and Variable Profiles

## Goal
`pcb_count` 기반 모델을 제거하고 `[[pcbs]]` + `[[coil_groups]]` 기반 구조로 스펙 SSOT를 재정의한다. 코일 형상은 `outer_x/outer_y`, `inner_margin`, `trace_profile/gap_profile`을 사용해 턴별 가변 피치/트레이스를 지원한다.

## In Scope
- `parameters.outer -> parameters.outer_x, parameters.outer_y` 전환
- `turn_count_max`, `inner_margin_x`, `inner_margin_y` 도입
- 함수형 프로파일 도입
  - `trace_profile = {mode="biased_linear", base, outer_bias, inner_bias, clamp_min}`
  - `gap_profile = {mode="biased_linear", base, outer_bias, inner_bias, clamp_min}`
- `[[coil_groups]]` 도입
  - `tx_dd` (count_mode=`2|4`)
  - `tx_vertical` (count_range=[0,4], `tx_vertical_span_mm` 포함)
  - `rx_dd` (count_fixed=2)
- 신규 자유변수
  - `tx_dd_pair_spacing_mm`
  - `rx_dd_pair_spacing_mm`
  - `tx_vertical_span_mm` (`0.0~15.0`)
- `[[pcbs]]` 유지
  - `id`, `role`, `position`, `rotation_deg`, `present`, `mounts`
- 총 8 PCB 예시(항상 존재 4 + optional 4) 명세화

## Out of Scope
- resolver 로직 변경
- geometry 생성 구현
- Tx/Rx Unite 실제 실행
- PCB 간 직렬 연결선 생성

## Spec/Type Changes
- 제거
  - `parameters.pcb_count`
  - 단일 `trace`, `gap`, `turns`
- 추가
  - `parameters.outer_x`, `parameters.outer_y`
  - `parameters.turn_count_max`
  - `parameters.inner_margin_x`, `parameters.inner_margin_y`
  - `parameters.trace_profile`, `parameters.gap_profile`
  - `parameters.tx_dd_pair_spacing_mm`
  - `parameters.rx_dd_pair_spacing_mm`
  - `parameters.tx_vertical_span_mm`
  - `[[coil_groups]]`: `kind`, `count_mode|count_fixed|count_range`, `instance_transforms`
  - `[[pcbs]]`: `mounts` 필드
- 고정 제약
  - `tx_vertical` 활성 인스턴스는 0~4
  - `tx_dd`는 2 또는 4
  - `rx_dd=2`
  - 총 코일 수 `<= 10`

## Implementation Steps
1. `examples/type1.toml`을 새 스펙으로 교체한다.
2. `[[coil_groups]]` 3개를 필수로 선언한다.
3. `tx_dd`의 count mode(2|4)를 명시한다.
4. `tx_vertical`의 count range(0~4)와 `tx_vertical_span_mm`를 명시한다.
5. `rx_dd_pair_spacing_mm`와 `tx_dd_pair_spacing_mm`를 명시한다.
6. `[[pcbs]]` 8개 인스턴스를 선언하고 4개 optional을 `present=[true,0,1,2]`로 지정한다.
7. always-on PCB는 `present=[true,1,1,1]`로 통일한다.
8. `mounts` 문법(`tx_dd:0`, `tx_vertical:*` 등)을 예시로 고정한다.
9. README에 파라미터 의미와 제약식을 반영한다.

## Validation Rules
- `coil_groups.kind`는 `{tx_dd, tx_vertical, rx_dd}`만 허용
- `tx_dd`는 count mode `{2,4}`만 허용
- `tx_vertical`은 count range `[0,4]`, span `[0,15]`만 허용
- `rx_dd`는 count_fixed=2만 허용
- `rx_dd_pair_spacing_mm > 0`, `tx_dd_pair_spacing_mm > 0`
- profile `clamp_min > 0`
- `outer_x > 0`, `outer_y > 0`, `inner_margin_x >= 0`, `inner_margin_y >= 0`
- `present` 후보는 0/1만 허용

## Test Cases
- 스펙 파싱 전 문서검토로 그룹/마운트 구조를 오해 없이 이해 가능한지 확인
- 8 PCB 예시(항상 4 + optional 4)에서 규칙이 일관적인지 확인
- `(tx_dd, tx_vertical, rx_dd)=(4,4,2)` 허용, `(4,5,2)` 거부 규칙 확인
- `tx_vertical_span_mm=0/15` 경계 규칙 확인
- profile/inner_margin/spacing 필드 누락 시 에러 메시지 확인

## Exit Criteria
- 신규 TOML 예시 하나로 그룹/PCB/프로파일/간격 구조를 완전 표현한다.
- 스펙 문서에 수치 제약이 모두 명시된다.
- 구현자가 추가 의사결정 없이 Phase 2 착수 가능하다.

## Risks and Rollback
- 리스크: 구 스펙(`pcb_count`, 단일 trace/gap/turns`)과 혼용 시 혼란
- 대응: 구 필드 사용 시 명시적 unsupported 에러 정책 문서화
- 롤백: 예시 TOML만 임시 병행 가능하나 SSOT는 신규 스펙으로 고정
