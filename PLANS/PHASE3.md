# PHASE3 - 공통 정책/인터페이스 전환 (SSOT/재현성 보강)

## 목표
- PHASE4~PHASE9 전 단계에 공통 적용되는 SSOT/재현 계약을 고정한다.
- TOML 외부 의사결정(숨은 파생, 강제 오버라이드)을 금지한다.
- 재현 경로를 `TOML`과 `manifest JSON` 두 축으로 동시에 지원한다.
- 형상 비의존 단계(영역/경계/포트/해석/결과/검증)를 type1/type2 공용 파이프라인으로 표준화한다.

## 공통 정책
- SSOT 1:1 매핑 강제:
  - 하나의 sampled 변수를 코드에서 여러 독립 설계변수로 암묵 파생하지 않는다.
  - 설계변수는 TOML path와 1:1 대응해야 하며, 파생은 TOML에 명시된 식으로만 허용한다.
- no max-override:
  - sampled 파라미터를 코드에서 `max/end` 값으로 강제 치환하지 않는다.
  - 특히 `rx_region_thickness_mm`는 sampled 값을 그대로 사용한다.
- `trace/gap` 정책:
  - 직접 입력으로 바꾸지 않고 `band_ratio`, `metal_ratio`, `base_outer` 파생식을 유지한다.

## 재현 정책 (이중 경로)
- `manifest JSON` replay를 유지한다.
- `TOML` replay를 지원한다.
- `frozen TOML` 정의:
  - 전체 스키마 구조를 유지한다.
  - 모든 `range`를 `[is_integer, selected_value, selected_value, 1]`로 고정한다.
  - 경량 최소키 TOML은 이번 범위에서 지원하지 않는다.
- frozen TOML 재실행의 합격 기준은 `형상 동일`이다.
- `design_id` 완전 동일성은 재현 합격 조건에서 제외한다.

## Public API / 인터페이스 변경
- spec_version: `0.1.7 -> 0.1.8`
- 제거 경로:
  - `coil_shape.outer_x`
  - `coil_shape.outer_y`
  - `coil_spacing.tx_dd_pair_spacing_mm`
  - `coil_spacing.rx_dd_pair_spacing_mm`
- 추가 경로:
  - `coil_shape.tx_dd.outer_x`
  - `coil_shape.tx_dd.outer_y`
  - `coil_shape.tx_vertical.outer_x`
  - `coil_shape.tx_vertical.outer_y`
  - `coil_shape.rx_dd.outer_x`
  - `coil_shape.rx_dd.outer_y`
  - `coil_spacing.tx_dd_pair_spacing_ratio`
  - `coil_spacing.rx_dd_pair_spacing_ratio`
- 공용 EM 인터페이스 추가:
  - `run_em_pipeline(hfss, modeler, em_input, em_policy) -> EmPipelineResult`

## GeometryMetadata / 공용 계약 확장
- `em_ready_objects`:
  - `tx_conductors`, `rx_conductors`, `fr4_objects`, `scene_bbox_source_objects`
- `em_endpoints`:
  - TX/RX 포트 생성용 시작/종단 후보
- `em_context`:
  - plane/축 정보, 방향성, path provenance
- `em_policy` 기본값:
  - `radiation_margin_mm=3500`
  - setup `6.78MHz`, sweep `1~42MHz`
  - validation gate `hard fail`
- `EmPipelineResult`:
  - `groups`, `series`, `subtract`, `boundary`, `ports`, `analysis`, `post_templates`, `validation_report`

## 0.1.8 경로 변경표
| 목적 | 기존 경로 (제거) | 신규 경로 |
|---|---|---|
| TX DD outer X | `coil_shape.outer_x` | `coil_shape.tx_dd.outer_x` |
| TX DD outer Y | `coil_shape.outer_y` | `coil_shape.tx_dd.outer_y` |
| TX Vertical outer X | `coil_shape.outer_x` | `coil_shape.tx_vertical.outer_x` |
| TX Vertical outer Y | `coil_shape.outer_y` | `coil_shape.tx_vertical.outer_y` |
| RX DD outer X | `coil_shape.outer_x` | `coil_shape.rx_dd.outer_x` |
| RX DD outer Y | `coil_shape.outer_y` | `coil_shape.rx_dd.outer_y` |
| TX DD pair spacing | `coil_spacing.tx_dd_pair_spacing_mm` | `coil_spacing.tx_dd_pair_spacing_ratio` |
| RX DD pair spacing | `coil_spacing.rx_dd_pair_spacing_mm` | `coil_spacing.rx_dd_pair_spacing_ratio` |

## SelectedParameters 계약
- 공통 `outer_x/outer_y`를 제거한다.
- 그룹별 `outer_x/outer_y`를 별도 필드로 유지한다.
- spacing은 ratio와 파생 mm를 모두 추적 가능하도록 보관한다.
- `repro_mode`(`sampled_toml`, `frozen_toml`, `manifest_json`)를 metadata 계약에 포함한다.

## DD spacing ratio 파생식/하드 제약
- 파생식:
  - `tx_dd_pair_spacing_mm = tx_dd_pair_spacing_ratio * tx_region_outer_h_mm`
  - `rx_dd_pair_spacing_mm = rx_dd_pair_spacing_ratio * rx_region_outer_h_mm`
- 운영 범위:
  - `0.0 <= tx_dd_pair_spacing_ratio <= 0.12`
  - `0.0 <= rx_dd_pair_spacing_ratio <= 0.03`
- selection hard check (geometry 이전 실패):
  - `tx_dd` 활성(`selected_count > 0`)일 때  
    `2*tx_dd.outer_y + tx_dd_pair_spacing_mm <= tx_region_outer_h_mm`
  - `rx_dd` 활성(`selected_count > 0`)일 때  
    `2*rx_dd.outer_x + rx_dd_pair_spacing_mm <= rx_region_outer_w_mm`
- 위반 시 `SelectionConstraintError`로 즉시 실패한다.

## 실패/호환 규약
- 구버전 자동 업컨버전은 하지 않는다.
- `0.1.8` 미만 또는 제거된 경로 입력 시 명시적 버전/경로 오류를 반환한다.
- selection 실패 메시지에는 `path`, `ratio`, `spacing_mm`, `lhs/rhs`를 포함한다.
- type1 전용 이름/축/경로를 공용 EM 모듈에 하드코딩하지 않는다.

## 구현 순서 (공용 EM 파이프라인)
1. `backend/pyaedt/em_pipeline/` 신설
   - `contracts.py`
   - `grouping.py`, `series.py`, `subtract.py`, `boundary_port.py`, `analysis.py`, `validate.py`
   - `runner.py` (`run_em_pipeline`)
2. type1 geometry에서 공용 계약 객체를 구성하고 `run_em_pipeline` 호출
3. type1 직결 구현을 단계별로 공용 모듈로 이동
4. type2 온보딩 문서/템플릿 추가
   - geometry 출력만 맞추면 공용 EM 파이프라인을 재사용하도록 규약화
5. 공용화 완료 후 type1 내부 중복 단계 제거

## 다음 단계
- PHASE4~PHASE9는 본 문서 정책을 참조하며, 공통 정책 중복 서술은 하지 않는다.
