# TX Rect/Void Type2 STEP 스펙

이 스펙은 `examples/type2/type2.toml`의 `[[modeled_objects]]`
`role = "tx_single_coil"` 항목으로 정의되는 build123d STEP authoring
계약이다. 별도 standalone example TOML은 public input이 아니다.

## 목적
- 단일 TX 직사각형 스파이럴 코일 footprint를 생성한다.
- 코일은 외곽 직사각형과 이동 가능한 void keepout 직사각형으로 표현한다.
- type2 v1은 type1 TX DD baseline에 맞춘 단층 copper coil만 지원한다.
- STEP export는 PCB body 1개와 fused copper body 1개를 생성해야 한다.
- Type1에서 해결한 same-corner terminal 문제를 그대로 따른다. `D_ccw_to_d`
  같은 path는 시작/끝을 코너 중심에 직접 두지 않고 다음 ring 좌표로 seed해,
  outer corner와 inner terminal이 중간 shortcut으로 붙지 않게 한다.

## TOML 계약
- `design.units`는 `"mm"`여야 한다.
- `modeled_objects.outer_x_mm`와 `modeled_objects.outer_y_mm`는 각각 mm
  단위 외곽 치수다. 외곽 Y는 ratio가 아니라 canonical mm 값이다.
- `pcb_thickness_mm = 1.6`, `copper_thickness_mm = 0.1`이 type2 baseline이다.
- `turn_count`는 1..4만 지원한다.
- `layer_count`는 type2 v1에서 반드시 1이어야 한다. 다층 coil은 via,
  층간 terminal, layer polarity 계약이 생기기 전까지 fail-fast한다.
- `layer_gap_mm`는 다층 확장을 위한 reserved/fixed field이며 현재 export
  geometry에는 영향을 주지 않는다.
- `void_*_over_*` 필드는 realized outer dimensions 대비 비율로 void 크기와
  중심을 정의한다.
- type2 v1은 type1 TX DD처럼 centered rectangular spiral만 지원하므로
  `void_center_x_over_outer_x`와 `void_center_y_over_outer_y`는 0으로 고정한다.
- `margin_ratio`는 대응하는 outer axis 대비 비율로 void-to-outer 최소
  clearance를 정의한다.
- `metal_fill_factor`는 각 side-local pitch cell에서 copper trace가 차지하는
  비율이며 0.15..0.60 범위여야 한다.
- realized trace width는 모든 side에서 최소 0.5 mm 이상이어야 한다.
- `terminal_path`는 `<outer>_<cw|ccw>_to_<inner>` 형식을 지원하며 v1에서는
  matching corner만 허용한다. type2 기본값은 `D_ccw_to_d`다.

## Type1-Derived Routing Contract
- Type1 neo TX DD는 centerline을 먼저 만들고, AEDT
  `create_polyline(..., xsection_type="Rectangle")`로 single trace를 생성한다.
- Type2 STEP export도 같은 centerline contract를 사용한다. Segment boxes는
  debug/decomposition payload이고, 최종 exported copper는 fused `tx_copper_l0`
  하나다.
- 각 segment box는 centerline endpoint에서 끊기지 않고 진행 방향 양끝으로
  half-trace만큼 연장된다. 이 corner-cap 규칙이 있어야 centerline 중심끼리
  붙는 모양이 아니라 trace 꼭짓점끼리 이어진다.
- Same-corner terminal path는 전용 planner를 사용한다. 단순히 outer corner에서
  한 바퀴를 돈 뒤 같은 corner로 직선 연결하지 않는다.
- Outer terminal이 outer rectangle의 실제 corner에 남으면 adjacent turn이나
  terminal tail이 corner에서 short될 수 있으므로, type1처럼 next-ring
  coordinate로 seed한다.
- Non-adjacent copper segment rectangle이 겹치면 turn-to-turn short이므로
  export 전에 즉시 실패한다.

## 출력
- `examples/type2/generate_type2_step.py`는 기본적으로 `run/step/type2/`
  아래에 object-level STEP과 metadata ledger를 기록한다.
- `entry/export_tx_rect_void_step.py`는 같은 type2 TOML에서 modeled
  `tx_single_coil`만 직접 export하는 얇은 CLI다.
- metadata JSON은 realized parameters, bounds, debug `boxes`, single-entry
  `modeled_objects`, 그리고 expected exported body 정보를 담는다.
- expected body contract:
  - `expected_exported_body_names = ["tx_pcb_l0", "tx_copper_l0"]`
  - `expected_exported_body_count = 2`
- `boxes`는 export 전 internal primitive decomposition/debug payload다. STEP
  copper body는 segment boxes를 build123d에서 fuse한 `tx_copper_l0`이어야 한다.

### `modeled_objects[0]` 필드

| Field | Value / Meaning |
| --- | --- |
| `object_id` | 고정값 `tx_rect_void_coil`. |
| `role` | 고정값 `tx_single_coil`. |
| `material` | 고정값 `composite`. |
| `model_state` | 고정값 `true`. |
| `step_path` | export된 STEP 파일의 serialized path string이다. |
| `expected_exported_body_names` | import diff count 검증용 expected body names다. |
| `expected_exported_body_count` | expected body names 수와 같아야 한다. |
| `canonical_coordinates.*` | local frame bounds와 layer z positions다. |
| `terminal_metadata.*` | terminal path, corner, direction, start/end centerline metadata다. |

## Modeled Import Smoke Handoff
- adapter 입력은 metadata JSON의 `modeled_objects[0]`와 같은 STEP import 후
  계산한 `imported_object_names` diff다.
- import smoke는 `imported_object_names` 수가 `expected_exported_body_count`와
  다르면 즉시 실패한다.
- adapter는 metadata의 role, coordinates, terminal semantics를 유지하고,
  AEDT geometry를 역산해 의미를 복원하지 않는다.

## 범위 제외
- HFSS ports, sources, solving.
- legacy `tx_dd` 및 `tx_vertical` spec field와의 호환성.
- multi-layer TX coil export.
- global placement transform.
