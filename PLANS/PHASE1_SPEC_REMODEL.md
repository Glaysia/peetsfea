# Phase 1 - Spec Remodel and Baseline Rebase

## Goal
현재 MVP 스펙을 Phase 2~4 확장에 견딜 수 있는 SSOT로 재정의한다. 핵심은 `[[pcbs]] + [[coil_groups]]` 구조 전환이며,
이미 반영된 non-model size envelope(`tv/tx.region/rx.region/wall/floor`)를 기반선으로 포함한다.

## Baseline (Already Done)
- `design_id`가 `unique_hash8_toml_space_hash8_seed` 형식으로 변경됨.
- `examples/type1.toml`에 non-model size envelope 항목이 count 포맷으로 추가됨.
- 코일 연결 레이어(bottom link/via) 생성 로직 제거됨.

Phase 1은 위 변경을 되돌리지 않고, 그 위에 스펙 리모델을 진행한다.

## In Scope
- `parameters.outer -> parameters.outer_x, parameters.outer_y` 전환.
- `turn_count_max`, `inner_margin_x`, `inner_margin_y` 도입.
- 함수형 프로파일 도입:
  - `trace_profile = {mode="biased_linear", base, outer_bias, inner_bias, clamp_min}`
  - `gap_profile = {mode="biased_linear", base, outer_bias, inner_bias, clamp_min}`
- `[[coil_groups]]` 도입:
  - `tx_dd` (count_mode=`2|4`)
  - `tx_vertical` (count_range=`[0,4]`, `tx_vertical_span_mm` 포함)
  - `rx_dd` (count_fixed=`2`)
- spacing 변수:
  - `tx_dd_pair_spacing_mm`
  - `rx_dd_pair_spacing_mm`
  - `tx_vertical_span_mm` (`0.0~15.0`)
- `[[pcbs]]` 명세:
  - `id`, `role`, `position`, `rotation_deg`, `present`, `mounts`
- 8 PCB 예시(항상 존재 4 + optional 4) 고정.
- non-model size envelope 경로는 유지하고 구조 재정의 시 충돌 없게 정합성 확보.

## Out of Scope
- resolver 구현 상세 (Phase 2).
- geometry 객체 생성 (Phase 3).
- Tx/Rx Unite/serial link 실제 실행 (Phase 4 이후).

## Spec Contract Changes
- 제거 예정:
  - `parameters.pcb_count`
  - 단일 `trace`, `gap`, `turns`
- 추가 예정:
  - `parameters.outer_x`, `parameters.outer_y`
  - `parameters.turn_count_max`
  - `parameters.inner_margin_x`, `parameters.inner_margin_y`
  - `parameters.trace_profile`, `parameters.gap_profile`
  - `parameters.tx_dd_pair_spacing_mm`
  - `parameters.rx_dd_pair_spacing_mm`
  - `parameters.tx_vertical_span_mm`
  - `[[coil_groups]]`: `kind`, `count_mode|count_fixed|count_range`, `instance_transforms`
  - `[[pcbs]]`: `mounts`

## Work Packages
1. `examples/type1.toml`의 새 구조 초안 작성.
2. 필수 coil group 3종(`tx_dd`, `tx_vertical`, `rx_dd`) 선언.
3. `[[pcbs]]` 8개 구성(항상 4 + optional 4)과 `present` 규약 확정.
4. mounts 문법(`tx_dd:0`, `tx_vertical:*` 등) 확정.
5. README/PLANS/LONGTERM 문서 간 경로명 동기화.
6. 구 스펙 사용 시 unsupported 정책 문구 확정.

## Validation Rules
- `coil_groups.kind`는 `{tx_dd, tx_vertical, rx_dd}`만 허용.
- `tx_dd` count mode는 `{2,4}`만 허용.
- `tx_vertical` count range는 `[0,4]`, span은 `[0,15]`만 허용.
- `rx_dd`는 count_fixed=2만 허용.
- `tx_dd_pair_spacing_mm > 0`, `rx_dd_pair_spacing_mm > 0`.
- profile `clamp_min > 0`.
- `outer_x > 0`, `outer_y > 0`, `inner_margin_x >= 0`, `inner_margin_y >= 0`.
- 활성 총 코일 수 상한 `<= 10`.
- non-model size envelope 경로는 유지하되 coil spec 경로와 의미 충돌 금지.

## Test/Review Checklist
- 스펙 문서만으로 그룹/마운트 구조가 구현자에게 자명한지 리뷰.
- 8 PCB 예시에서 optional on/off와 mounts 규칙 일관성 확인.
- `(tx_dd, tx_vertical, rx_dd)=(4,4,2)` 허용, `(4,5,2)` 거부 규칙 확인.
- profile/inner_margin/spacing 누락 시 오류 메시지 계약 확인.

## Exit Criteria
- `examples/type1.toml` 하나로 그룹/PCB/profile/spacing/non-model envelope를 모두 표현.
- 문서에 수치 제약과 unsupported 정책이 명시.
- Phase 2 구현자가 추가 의사결정 없이 resolver 착수 가능.

## Risks and Rollback
- 리스크: 구 스펙과 신 스펙 혼용으로 resolver 전이 복잡도 증가.
- 대응: Phase 2에서 구 키셋 즉시 unsupported 처리.
- 롤백: 예시 TOML 병행은 가능하지만 SSOT는 신 스펙으로 고정.
