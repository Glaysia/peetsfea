# Phase 2 - Resolver and Manifest for Grouped Coil Determinism

## Goal
신규 스펙(`coil_groups`, `pcbs`, profile`)을 resolver에서 결정론적으로 해석하고, 선택 결과를 manifest/hash에 반영한다.

## In Scope
- `trace_profile/gap_profile` 파싱 및 정규화
- `tx_dd_count_mode` 선택(2|4)
- `tx_vertical_count` seed 기반 선택(0~4)
- `tx_vertical_span_mm`, `tx_dd_pair_spacing_mm`, `rx_dd_pair_spacing_mm` 해석
- PCB `present`를 seed 기반으로 결정
- `selected_coil_groups`, `selected_pcbs`를 manifest에 기록
- design_id payload에 그룹/존재/간격 결과를 포함

## Out of Scope
- geometry 객체 생성
- CAD 모델 변환/배치
- Unite/직렬 연결 수행

## Spec/Type Changes
- `SelectedParameters` 추가/변경
  - `outer_x`, `outer_y`, `turn_count_max`, `inner_margin_x`, `inner_margin_y`
  - `trace_profile`, `gap_profile`
  - `tx_dd_count_mode`, `tx_dd_pair_spacing_mm`
  - `tx_vertical_count`, `tx_vertical_span_mm`
  - `rx_dd_pair_spacing_mm`
- 신규 타입
  - `ResolvedCoilGroup` (kind, requested_count, selected_count, transforms, spacing)
  - `ResolvedPcbInstance` (id, role, position, rotation_deg, present, mounts)
- `Manifest` 추가
  - `selected_coil_groups: list[ResolvedCoilGroup]`
  - `selected_pcbs: list[ResolvedPcbInstance]`
- hashing 입력 확장
  - `selected_parameters + selected_coil_groups + selected_pcbs`

## Implementation Steps
1. `resolver.py`에서 구 파라미터 키를 제거하고 신규 키셋을 강제한다.
2. profile 값을 정규화(`mode`, `base`, `outer_bias`, `inner_bias`, `clamp_min`)한다.
3. `tx_dd_count_mode`를 `{2,4}`로 해석한다.
4. `tx_vertical_count`를 deterministic 선택한다.
5. `tx_vertical_span_mm`, `tx_dd_pair_spacing_mm`, `rx_dd_pair_spacing_mm`를 검증/선택한다.
6. 각 PCB의 `present`를 deterministic 선택한다.
7. `mounts` 유효성(존재하지 않는 group instance 참조 금지)을 검증한다.
8. `manifest.py` 타입을 확장하고 `run_design.py`에 기록한다.
9. `identity/hashing.py`에 새 payload를 반영한다.

## Validation Rules
- 동일 spec + seed => 동일 selected 결과
- `tx_dd_count_mode in {2,4}`
- `tx_vertical_count in [0,4]`
- `tx_vertical_span_mm in [0,15]`
- `tx_dd_pair_spacing_mm > 0`, `rx_dd_pair_spacing_mm > 0`
- 활성 총 코일 수 `<= 10`
- profile로 계산 가능한 모든 `trace_k`, `gap_k`가 `clamp_min` 이상이어야 함
- `mounts`는 선택된 group instance와 일치해야 함

## Test Cases
- resolver deterministic 테스트(동일 seed 동일 결과)
- seed 변경 시 `present`/`tx_vertical_count`/optional 선택만 변화 확인
- `(tx_dd, tx_vertical, rx_dd)=(4,4,2)` 허용, `(4,5,2)` 거부 테스트
- invalid profile(clamp_min<=0), invalid mounts, invalid spacing 에러 확인
- hashing에 새 선택 결과 반영 여부 검증

## Exit Criteria
- manifest만으로 실행에 필요한 group/pcb 선택 상태를 완전 재현 가능
- design_id가 그룹/존재/간격 선택 상태 변화를 반영
- 타입체크 및 resolver 단위 테스트 통과

## Risks and Rollback
- 리스크: hash 스키마 변경으로 기존 데이터셋과 ID 불연속
- 대응: spec version 명시적 bump 및 migration note 제공
- 롤백: 임시로 hash payload 축소 가능하지만 재현성 계약 약화
