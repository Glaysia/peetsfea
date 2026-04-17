---
title: tx-rect-void-step
created: 2026-04-17 @ 04:20
updated: 2026-04-17 @ 19:20
tags:
  - type2
  - tx-rect-void
  - step-export
---

# Rect/Void Type2 STEP 스펙

이 스펙은 `examples/type2_fixed.toml`의 `[[modeled_objects]]`
`role = "tx_single_coil"` / `role = "rx_single_coil"` 항목으로 정의되는 build123d STEP authoring
계약이다. 별도 standalone example TOML은 public input이 아니다.

## 목적
- 단일 TX/RX 직사각형 스파이럴 코일 footprint를 생성한다.
- 코일은 외곽 직사각형과 이동 가능한 void keepout 직사각형으로 표현한다.
- active TX path는 type1 routing contract를 재사용하는 multilayer parallel-bus single-coil을 지원하고, RX는 current milestone에서 single-layer만 지원한다.
- type2 scene export는 port sheet를 STEP body로 내보내지 않고 metadata로만 유지하며, TX에서는 optional explicit underlay tri-layer bodies를 scene layer에서 추가할 수 있다.
- canonical corner geometry는 square corner가 아니라 always-on `45-degree beveled blunt corner`다.
- Type1에서 해결한 same-corner terminal 문제를 그대로 따른다. `D_ccw_to_d`
  같은 path는 시작/끝을 코너 중심에 직접 두지 않고 다음 ring 좌표로 seed해,
  outer corner와 inner terminal이 중간 shortcut으로 붙지 않게 한다.

## TOML 계약
- `design.units`는 `"mm"`여야 한다.
- `modeled_objects.outer_x_mm`와 `modeled_objects.outer_y_mm`는 각각 mm
  단위 coil routing envelope 치수다. 외곽 Y는 ratio가 아니라 canonical mm 값이다.
- exported PCB body는 이 routing envelope를 그대로 쓰지 않고, generated copper
  layer의 최외곽 planar rectangle에서 파생된다.
- `pcb_thickness_mm = 1.6`, `copper_thickness_mm = 0.1`이 type2 baseline이다.
- `turn_count`는 1..4만 지원한다.
- `layer_count`는 TX에서 1 이상을 지원하며, multilayer TX는 start/end terminal column full-height bus를 쓰는 parallel-connected stack으로 문서화한다. RX는 current milestone에서 `1`만 허용한다.
- `layer_gap_mm`는 TX multilayer spacing과 derived terminal-stub rule에 직접 영향을 준다.
- `terminal_stub_length_mm` field는 public schema compatibility를 위해 유지되지만,
  current runtime stub 길이는 `layer_gap_mm * 0.8` derived rule을 canonical로 사용한다.
- `underlay_repeat_count`는 shared modeled-object field다.
  - canonical encoding은 `[true, 0, 8, 5]`
  - realized candidate set은 `{0, 2, 4, 6, 8}`
  - TX는 이 집합을 지원한다
  - RX는 current milestone에서 `0`만 허용한다
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
- Type2 STEP export도 same-corner seed planner를 재사용하지만, exported centerline은
  항상 blunt corner로 shaping된 뒤에 geometry authoring으로 넘어간다. sharp seed path는
  internal intermediate일 뿐 public/export contract가 아니다.
- blunt corner trim의 시작값은 type1 corner shaping 규칙을 따르되, inner corner가
  void keepout을 침범하면 trim을 줄여 45도 bevel을 유지한다.
- 최종 copper authoring의 live path는 blunt centerline 각 segment가 자기 polygon 안에
  join vertex를 직접 소유하는 `joined segment strip` 경로다. separate corner-join
  primitive는 두지 않고, 여기에 start/end terminal stub prism만 fuse한다.
- 재발 원인은 “segment polygon이 실제 owner인데도 separate join primitive나 debug
  `boxes`가 geometry owner처럼 읽히던 상태”였다. type2에서는 joined segment polygon
  하나만 live owner이고, 나머지는 모두 derived/debug state다.
- `boxes`는 canonical geometry가 아니라 final primitive set에서 파생된 debug AABB
  payload다. export가 `boxes`를 다시 읽어 copper를 재구성하면 안 된다.
- `tx_pcb_l0` / `rx_pcb_l0`는 generated copper decomposition의 layer-local planar
  bbox에서 직접 파생되며, extra FR4 overhang 없이 exact derived footprint를 사용한다.
- Same-corner terminal path는 전용 planner를 사용한다. 단순히 outer corner에서
  한 바퀴를 돈 뒤 같은 corner로 직선 연결하지 않는다.
- Outer terminal이 outer rectangle의 실제 corner에 남으면 adjacent turn이나
  terminal tail이 corner에서 short될 수 있으므로, type1처럼 next-ring
  coordinate로 seed한다.
- terminal stub는 trace width의 60% 정사각형 단면을 가지며, start/end segment
  안쪽으로만 조금 겹쳐 single fused copper solid를 보장한다.
- Non-adjacent planar segment strip footprint가 겹치면 turn-to-turn short이므로
  export 전에 즉시 실패한다.

## TX underlay scene-layer contract
- underlay는 `tx_rect_void` core routing engine의 책임이 아니라 type2 scene/export/import 계층의 책임이다.
- `underlay_repeat_count > 0`인 TX modeled object는 TX stack의 맨 아래 한 곳에만 explicit underlay tri-layer stack을 가진다. 각 PCB layer 아래에 복제되지 않는다.
- underlay 1 unit는 TX bottom-down 방향으로 다음 순서를 가진다.
  1. `MULL12060ferrite` / `0.20 mm`
  2. `PET_PSA` / `0.15 mm`
  3. explicit `vacuum` air body / `0.02 mm`
- first ferrite top face는 TX modeled object canonical minimum-Z plane에 닿아야 한다.
- later units는 같은 순서로 아래 방향으로 반복 적층된다.
- `u0`가 TX에 가장 가까운 첫 unit이다.
- TX underlay XY footprint canonical source는 actual exported PCB+copper union planar bounds다. `tx_region` full footprint나 별도 underlay margin은 canonical source가 아니다.
- exact body names:
  - `tx_underlay_ferrite_u{n}`
  - `tx_underlay_pet_psa_u{n}`
  - `tx_underlay_air_u{n}`
- `PET_PSA`는 air-like dielectric이며 explicit documented difference는 `permittivity = 2.8`이다.

## 출력
- `entry/generate_type2_step.py`는 기본적으로 `run/step/type2/`
  아래에 object-level STEP과 metadata ledger를 기록한다.
- `entry/export_tx_rect_void_step.py`는 같은 type2 TOML에서 modeled
  `tx_single_coil`만 직접 export하는 얇은 CLI다.
- metadata JSON은 realized parameters, bounds, debug `boxes`, single-entry
  `modeled_objects`, 그리고 expected exported body 정보를 담는다.
- type2 경로는 role별 placement owner를 가진다.
  - `tx_single_coil`: `tx_region` 내부 중앙-X, 중앙-Y, owner max-Z 접촉
  - `rx_single_coil`: `rx_region_actual` 내부 중앙-Y, 바닥 Z 접촉, owner max-X 접촉
- active example `examples/type2_fixed.toml`은 scene 전체를 global Z rebase한 상태를 canonical baseline으로 사용한다. 즉 `tx_region` 바닥면이 `z = 0`이고, generator/export는 이 explicit world-coordinate를 다시 정규화하지 않는다.
- canonical bounds는 input routing envelope가 아니라 실제 exported PCB+copper union
  bounds를 기록한다. 하단 Z는 PCB 바닥이 아니라 terminal stub 끝점까지 내려간다.
- expected body contract:
  - single-layer TX without underlay: `["tx_pcb_l0", "tx_copper_l0"]`
  - multilayer TX without underlay: `["tx_pcb_l0", ..., "tx_pcb_l{n}", "tx_copper_stack"]`
  - TX with underlay: append `tx_underlay_ferrite_u{n}`, `tx_underlay_pet_psa_u{n}`, `tx_underlay_air_u{n}` after the base TX body set
  - `rx_single_coil`은 current milestone에서 `["rx_pcb_l0", "rx_copper_l0"]`
- `boxes`는 export 전 internal primitive decomposition/debug payload다. STEP
  copper body는 planar trace와 terminal stub를 함께 fuse한 `tx_copper_l0` 또는 multilayer TX의 경우 `tx_copper_stack`이어야 한다.

### `modeled_objects[0]` 필드

| Field | Value / Meaning |
| --- | --- |
| `object_id` | role별 canonical id (`tx_rect_void_coil`, `rx_rect_void_coil`). |
| `role` | `tx_single_coil` 또는 `rx_single_coil`. |
| `plane` | `tx_single_coil`은 `XY`, `rx_single_coil`은 `YZ`. |
| `placement_owner_id` | `tx_region` 또는 `rx_region_actual`. |
| `material` | 고정값 `composite`. |
| `model_state` | 고정값 `true`. |
| `step_path` | export된 STEP 파일의 serialized path string이다. |
| `expected_exported_body_names` | import diff count 검증용 expected body names다. |
| `expected_exported_body_count` | expected body names 수와 같아야 한다. |
| `canonical_coordinates.*` | type2 scene absolute bounds와 layer z positions다. |
| `terminal_metadata.*` | plane-aware terminal path, corner, direction, `start_point_plane_mm` / `end_point_plane_mm` metadata다. |

## Modeled Import Smoke Handoff
- adapter 입력은 metadata JSON의 `modeled_objects[0]`와 같은 STEP import 후
  계산한 `imported_object_names` diff다.
- import smoke는 `imported_object_names` 수가 `expected_exported_body_count`와
  다르면 즉시 실패한다.
- adapter는 metadata의 role, coordinates, terminal semantics를 유지하고,
  AEDT geometry를 역산해 의미를 복원하지 않는다.
- type2 HFSS import는 modeled object를 다시 `move()`하지 않는다. export ledger가
  이미 최종 배치를 소유하고, import는 그 계약만 검증한다.
- TX underlay bodies는 explicit STEP imported solids다. port sheet는 반대로 metadata-driven HFSS reconstruction surface다.
- mesh ownership은 conductor-only다. `tx_copper_l0` / `tx_copper_stack`, `rx_copper_l0` 같은 conductor bodies만 mesh 대상이고 underlay slabs는 대상이 아니다.

## 범위 제외
- HFSS ports, sources, solving.
- legacy `tx_dd` 및 `tx_vertical` spec field와의 호환성.
- RX multilayer support.
- RX non-zero underlay support.
- arbitrary post-import placement repair.
