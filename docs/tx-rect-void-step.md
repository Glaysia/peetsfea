# TX Rect/Void STEP 스펙

이 초안 스펙은 standalone build123d STEP authoring 경로다. 기존 type1
PyAEDT/HFSS pipeline은 사용하지 않는다.

## 목적
- 단일 TX 직사각형 스파이럴 코일 footprint를 생성한다.
- 코일은 외곽 직사각형과 이동 가능한 void keepout 직사각형으로 표현한다.
- 활성 stacked PCB layer와 copper를 이후 수동 Ansys import용 STEP 파일로
  내보낸다.

## TOML 계약
- `design.units`는 `"mm"`여야 한다.
- `manufacturing.pcb_thickness_mm`와 `manufacturing.copper_thickness_mm`는
  고정된 양수 millimeter 값이어야 한다.
- `tx_coil.*.range`는 `[is_integer, start, end, count]` 형식을 사용한다.
- `tx_coil.layer_count`는 1, 2, 3으로 해석되어야 한다.
- `tx_coil.layer_gap_mm`는 최소 2.0 mm로 해석되어야 한다.
- `tx_coil.void_*_over_*` 필드는 realized outer dimensions 대비 비율로 void
  크기와 중심을 정의한다.
- `tx_coil.margin_ratio`는 대응하는 outer axis 대비 비율로 void-to-outer 최소
  clearance를 정의한다.
- `tx_coil.metal_fill_factor`는 각 side-local pitch cell에서 copper trace가
  차지하는 비율을 정의한다.
- `tx_coil.terminal_path`는 `<outer>_<cw|ccw>_to_<inner>` 형식을 지원하며
  `A-D`는 outer corners, `a-d`는 대응하는 void corners를 뜻한다. v1에서는
  `A_cw_to_a` 같은 matching corner만 허용한다.

## 출력
- CLI `entry/export_tx_rect_void_step.py`는 기본적으로 `run/step/` 아래에
  STEP 파일을 기록한다.
- metadata JSON 파일은 STEP 경로 옆에 기록되며 realized parameters, bounds,
  layer positions, generated box primitives를 담는다.
- metadata JSON은 기존 `realized`, `boxes` 외에도 single-entry
  `modeled_objects` proto-contract를 담는다.
- `modeled_objects[0]`는 최소한 `object_id`, `role`, `material`,
  `model_state`, `step_path`, canonical coordinates, terminal metadata를
  가진다.

### `modeled_objects[0]` 필드

아래 필드는 모두 현재 export local frame 기준이다. 이 prototype에서는 frame
origin이 `(0, 0, 0)`이고, global placement transform은 아직 범위 밖이다.

| Field | Value / Meaning |
| --- | --- |
| `object_id` | 고정값 `tx_rect_void_coil`. |
| `role` | 고정값 `tx_single_coil`. |
| `material` | 고정값 `composite`. PCB slab와 copper box를 묶은 modeled object 의미다. |
| `model_state` | 고정값 `true`. 이 STEP artifact는 modeled object다. |
| `step_path` | export된 STEP 파일의 serialized path string이다. |
| `canonical_coordinates.frame_origin_xyz` | local prototype frame origin. 현재 `(0, 0, 0)`이다. |
| `canonical_coordinates.outer_bounds_min_xyz` | modeled object outer bounds의 local minimum xyz다. |
| `canonical_coordinates.outer_bounds_max_xyz` | modeled object outer bounds의 local maximum xyz다. |
| `canonical_coordinates.outer_bounds_size_xyz` | modeled object outer bounds size xyz다. |
| `canonical_coordinates.pcb_layer_z_positions_mm` | 각 PCB slab bottom face의 local z positions다. |
| `canonical_coordinates.copper_layer_z_positions_mm` | 각 copper layer bottom face의 local z positions다. |
| `terminal_metadata.path` | 선택된 terminal path string이다. |
| `terminal_metadata.outer_corner` | terminal이 시작하는 outer corner label이다. |
| `terminal_metadata.inner_corner` | terminal이 끝나는 matching inner corner label이다. |
| `terminal_metadata.direction` | winding traversal direction이다. |
| `terminal_metadata.start_point_xy_mm` | centerline 시작점의 local XY 좌표다. |
| `terminal_metadata.end_point_xy_mm` | centerline 종료점의 local XY 좌표다. |

- `boxes`는 registry object가 아니다. build123d scene을 구성하는 internal
  primitive decomposition/debug payload다.
- future modeled import smoke에서는 `modeled_objects[0]`가 canonical modeled
  object ledger source가 되고, `boxes`는 디버그/검증 보조 정보로만 남는다.

## 범위 제외
- PyAEDT, HFSS launch, AEDT import, ports, sources, solving.
- legacy `tx_dd` 및 `tx_vertical` spec field와의 호환성.
- `imported_object_names`, `em_mapping_role`, port/source assignment, multi-coil
  composition, global placement transform.
