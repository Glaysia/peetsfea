# PHASE4 - 오브젝트 그룹화 + Resolver/Selection 입력 계약

## 목표
- HFSS 그룹화 규칙과 Selection/Resolver 입력 계약을 동시에 고정한다.
- 그룹별 outer 전환 및 spacing ratio 하드체크를 geometry 이전에 완료한다.
- 공용 EM 파이프라인 입력(`em_context` provenance/path 정보) 생성 계약을 고정한다.

## 범위
- HFSS 그룹 분류:
  - `grp_scene`, `grp_tx_coils`, `grp_rx_coils`, `grp_fr4`, `grp_tx_series_aux`, `grp_rx_series_aux`
- 직렬연결 입력 표준화:
  - `group_endpoints`, `group_objects`, `coil_polarity`
- Resolver 입력경로 전환:
  - 공통 `outer_x/outer_y` 참조 금지
  - 그룹별 경로 참조 의무 (`tx_dd`, `tx_vertical`, `rx_dd`)
- `rx_region_thickness_mm` 정책:
  - sampled 값 유지 (강제 max 오버라이드 금지)

## Selection/Resolver 파생 계약
- spacing ratio 파생:
  - `tx_dd_pair_spacing_mm = tx_dd_pair_spacing_ratio * tx_region_outer_h_mm`
  - `rx_dd_pair_spacing_mm = rx_dd_pair_spacing_ratio * rx_region_outer_h_mm`
- 그룹별 기하 파생:
  - `effective_outer_y(tx_vertical) = min(tx_vertical.outer_y, tx_region_vertical_z_mm)`
  - `effective_outer_y(tx_dd/rx_dd) = group.outer_y`
  - `base_outer = min(group.outer_x, effective_outer_y)`
  - `band_mm = band_ratio * base_outer`
  - `pitch_mm = band_mm / turn_count_max`
  - `trace_mm = pitch_mm * metal_ratio`
  - `gap_mm = pitch_mm * (1 - metal_ratio)`

## Selection 하드체크
- `tx_dd` 활성(`selected_count > 0`)일 때:
  - `2*tx_dd.outer_y + tx_dd_pair_spacing_mm <= tx_region_outer_h_mm`
- `rx_dd` 활성(`selected_count > 0`)일 때:
  - `2*rx_dd.outer_x + rx_dd_pair_spacing_mm <= rx_region_outer_w_mm`
- 실패 시:
  - `SelectionConstraintError`
  - 필수 메시지 필드: `path`, `ratio`, `spacing_mm`, `lhs`, `rhs`

## 메타데이터 계약
- `hfss_groups` 필드 유지
- `group_outer_mapping_passed` 선검증 결과를 이후 단계에서 재사용 가능하도록 기록
- `em_context.path_provenance`:
  - selection/제약에 사용된 핵심 TOML path를 공용 파이프라인에 전달
- `em_context.axis_contract`:
  - 포트/경계 산출에 필요한 축/plane 규약 전달

## 완료 기준
- 그룹화 규칙과 resolver 입력 경로가 deterministic하게 문서화된다.
- selection 하드체크가 geometry 이전 게이트로 고정된다.
- type1/type2가 동일 계약으로 공용 EM 파이프라인 입력을 만들 수 있다.
