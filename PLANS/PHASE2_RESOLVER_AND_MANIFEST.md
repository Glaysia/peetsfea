# Phase 2 - Resolver and Manifest Rework for Determinism

## Goal
Phase 1 스펙을 deterministic하게 해석하고, 선택 결과를 manifest/hash에 완전 반영한다.
이 페이즈에서 resolver를 확장 가능한 구조로 재작성해 Phase 3 geometry를 위한 입력 계약을 잠근다.

## Baseline (Already Done)
- `design_id` 조합 규칙은 이미 `unique_hash + toml_space_hash + seed`.
- manifest/geometry metadata에 `design_unique_hash`, `toml_space_hash` 필드 존재.
- non-model size envelope는 TOML에 이미 존재하지만 resolver는 아직 반영 전.

## In Scope
- 경로 카탈로그 기반 resolver 구조 도입.
- `trace_profile/gap_profile` 파싱/정규화.
- `tx_dd_count_mode` 선택(2|4).
- `tx_vertical_count` deterministic 선택(0~4).
- `tx_vertical_span_mm`, `tx_dd_pair_spacing_mm`, `rx_dd_pair_spacing_mm` 선택/검증.
- PCB `present` deterministic 선택.
- non-model size envelope 선택값을 manifest의 selected payload에 포함.
- 제약식 추가: `TX coil outer < TX region`.
- `selected_coil_groups`, `selected_pcbs`를 manifest에 기록.

## Out of Scope
- geometry 객체 생성/배치.
- CAD 변환.
- Unite/직렬 연결 실제 실행.

## Type and Contract Changes
- `SelectedParameters` 확장:
  - coil/profile/spacing 관련 신규 키.
  - `tv_*`, `tx_region_*`, `rx_region_*`, `wall_*`, `floor_*` 키.
- 신규 타입:
  - `ResolvedCoilGroup` (kind, requested_count, selected_count, transforms, spacing)
  - `ResolvedPcbInstance` (id, role, position, rotation_deg, present, mounts)
- `Manifest` 확장:
  - `selected_coil_groups: list[ResolvedCoilGroup]`
  - `selected_pcbs: list[ResolvedPcbInstance]`
- hash payload 확장:
  - `selected_parameters + selected_coil_groups + selected_pcbs`
  - 기존 `design_id` 조합 포맷은 유지.

## Work Packages
1. resolver 경로 카탈로그 구현:
   - spec path -> internal key -> type/range policy.
2. profile 정규화기 구현:
   - `mode`, `base`, `outer_bias`, `inner_bias`, `clamp_min`.
3. group count 해석기 구현:
   - `tx_dd`, `tx_vertical`, `rx_dd`.
4. PCB present 선택기 구현.
5. mounts 유효성 검증기 구현.
6. non-model size envelope 선택 통합.
7. manifest 타입/생성 로직 업데이트.
8. hash payload 반영 업데이트.
9. 오류 메시지 표준화(`path` 포함).

## Validation Rules
- 동일 spec + seed => 동일 selected 결과.
- `tx_dd_count_mode in {2,4}`.
- `tx_vertical_count in [0,4]`.
- `tx_vertical_span_mm in [0,15]`.
- `tx_dd_pair_spacing_mm > 0`, `rx_dd_pair_spacing_mm > 0`.
- 활성 총 코일 수 `<= 10`.
- profile 유도값 `trace_k`, `gap_k >= clamp_min`.
- `mounts`는 선택된 group instance와 일치.
- `outer < min(tx_region_outer_w_mm, tx_region_outer_h_mm)`.

## Test Matrix
- deterministic 테스트:
  - 동일 seed 재현.
  - seed 변경 시 count/present 선택 변화 확인.
- schema/validation 테스트:
  - invalid profile, mounts, spacing, group count.
  - invalid envelope range/path.
- constraint 테스트:
  - TX 영역 경계(`outer == min(...)`) 실패.
- hash/manifest 테스트:
  - payload 변경 시 `design_unique_hash` 변경.
  - `design_id` 포맷 유지.

## Exit Criteria
- manifest만으로 group/pcb/envelope 선택 상태 완전 재현 가능.
- hash payload가 선택 상태 변화를 반영.
- resolver 단위 테스트, mypy, ruff 전부 통과.

## Risks and Rollback
- 리스크: hash payload 확장으로 기존 데이터셋 ID 불연속.
- 대응: spec version bump + migration note.
- 리스크: resolver 리팩터로 기존 MVP 경로 회귀.
- 대응: 구 스펙 입력에 대한 explicit unsupported 테스트 추가.
