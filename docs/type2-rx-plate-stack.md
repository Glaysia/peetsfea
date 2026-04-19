---
title: type2-rx-plate-stack
created: 2026-04-19 @ 18:05
updated: 2026-04-19 @ 15:55
tags:
  - type2
  - rx
  - plate-stack
  - step-export
---

# Type2 RX Plate Stack

이 문서는 active `examples/type2_fixed.toml`, `examples/type2_sweep.toml`의 RX modeled object
`role = "rx_plate_stack"` 계약을 설명한다. shared TX/RX plate-stack runtime boundary는
[`docs/type2-plate-stack.md`](type2-plate-stack.md)에 정리되어 있다. 이 역할은
geometry/export와 setup-ready full-EM-ready build를 지원한다. import-only helper는 geometry inspection /
import-only surface다.
TX/RX shared generation ownership과 thickness baseline canonical source는 shared 문서이며,
이 문서는 RX role-local geometry/export detail만 다룬다.

## Runtime Boundary
- `type2_step_setup_ready`의 active default build path는 exact plate-stack pair를
  setup-ready full-EM-ready branch로 처리한다.
- setup-ready facade는 plate-stack exact pair에서도 아래 후반부를 coil branch와 동일 실행한다.
  - post-import mesh
  - radiation boundary
  - explicit lumped ports
  - source phase
  - analysis/report
  - `validate_pipeline()`
  - `ValidateDesign()`
  - final save
- RX plate-stack port는 reconstructed `rx_plate_port_sheet`를 사용하고 numeric naming은 `2/2_T1`다.
- `terminal_metadata.kind = "stub_port"`는 import-only reconstructed sheet를 위한 metadata고,
  setup-ready full-EM-ready branch도 동일 reconstructed sheet contract를 사용한다.
- plate-stack mesh owner는 conductor-only exact set이며 plate-stack pair에서는
  `tx_plate_copper`, `rx_plate_copper`만 mesh target이다.
- underlay solids, `*_pcb_wall`/`*_pcb_coil`, reconstructed port sheet는 mesh 대상이 아니다.
- `build_type2_em_input()`는 plate-stack exact pair를 reject하지 않고 `EmPipelineInput`을 조립한다.
- active example baseline에서 `pcb_total_thickness_mm`는 RX/TX 모두 `0.4 mm`다.
  legacy `1.6/0.4` split guidance는 active plate-stack contract가 아니다.

## 목적
- `rx_region_max` full `YZ` footprint를 그대로 쓰는 넓은 RX copper/PCB stack을 만든다.
- RX는 더 이상 `tx_rect_void` coil bridge를 통과하지 않는다.
- RX ferrite family는 effective-thickness collapse가 아니라 literal 10-set solid taxonomy를 쓴다.
  Export handoff에서는 literal sets가 material별 united body 3개로 collapse된다.

## TOML 계약
- `object_id = "rx_plate_stack"`
- `role = "rx_plate_stack"`
- `material = "composite"`
- `model_state = true`
- `pcb_total_thickness_mm > copper_thickness_mm > 0`
- `ferrite_set_count = 10`
- `turn_count`는 정수 range고 realized 값은 `>= 2`여야 한다.
- `metal_fill_factor`는 float range고 realized 값은 `> 0`, `<= 0.6`여야 한다.
- `shoe_depth_mm`는 active RX plate-stack public field가 아니다. plate-stack modeled object에
  남아 있으면 loader가 removed field로 즉시 실패한다.
- coil-only field `outer_*`, `layer_count`, `terminal_path`, `void_*`, `margin_ratio`,
  `underlay_repeat_count`, `underlay_gap_mm`, `wall_parallel_stack_present`는 선언하면 안 된다.

## Geometry Contract
- placement owner는 `rx_region_max`다.
- footprint source of truth는 `rx_region_max` full `YZ` size다.
- stack는 `rx_region_max.min_x`에 붙고 `+X` 방향으로 자란다.
- wall/coil-side PCB와 copper stripe는 owner full `Z` height를 그대로 사용한다.
- `pcb_total_thickness_mm`은 copper 1 layer를 포함한 board total thickness다.
  - wall-side board: `rx_copper_wall_t*`, `rx_pcb_wall`
  - coil-side board: `rx_pcb_coil`, `rx_copper_coil_t*`
  - epoxy thickness는 `pcb_total_thickness_mm - copper_thickness_mm`
- ferrite/PET_PSA/vacuum set는 literal 10회로 export되고, 각 ferrite는 유전체가 앞뒤로 오도록
  interleaved order를 쓴다.
  - ferrite `0.20 mm`
  - PET/PSA `0.15 mm`
  - vacuum `0.02 mm`
- `N = realized turn_count`
- `pitch_z = rx_region_max.size_z / (N + 0.5)`
- `trace_height_z = pitch_z * metal_fill_factor`
- `stripe_center_offset_z = (pitch_z - trace_height_z) / 2`
- wall-side stripe `t{i}`는 `z_min + i * pitch_z + stripe_center_offset_z`에서 시작한다.
- coil-side stripe `t{i}`는 `z_min + pitch_z / 2 + i * pitch_z + stripe_center_offset_z`에서 시작한다.
- wall-side와 coil-side stripe count는 모두 `N`개다.
- side bridge `rx_bridge_s*`는 `Y=max/min`을 번갈아 쓰며
  `wall_t0 -> coil_t0 -> wall_t1 -> ... -> wall_t{N-1} -> coil_t{N-1}`를 잇는다.
- bridge `z` window는 owner `Z` bounds를 먼저 clip하고, 같은 edge(`Y=max` or `Y=min`)의
  이전 bridge upper bound를 하한으로 써서 same-edge neighboring bridge positive-volume overlap을 금지한다.
- terminal stub `rx_stub_in`은 wall-side `t0`, `rx_stub_out`은 coil-side `t{N-1}`에 붙고
  둘 다 `-Y` 방향으로 `5.0 mm` 돌출한다.
- wall/coil stripes, bridges, terminal stubs는 final export 전에 `rx_plate_copper`로 unite된다.
  `rx_copper_wall_t*`, `rx_copper_coil_t*`, `rx_bridge_s*`, `rx_stub_in/out` labels는
  pre-unite source/provenance labels이며 final STEP/import/mesh body names가 아니다.
- total thickness guard:
  - `2 * pcb_total_thickness_mm + 10 * (0.20 + 0.15 + 0.02) <= rx_region_max.size_x`

## Exact Body Order
Plate-stack final handoff keeps role-level bodies plus merged ferrite materials.
Pre-unite segment and per-set labels are provenance-only and do not belong here.

1. `rx_plate_copper`
2. `rx_pcb_wall`
3. `rx_stack_pet_psa`
4. `rx_stack_ferrite`
5. `rx_stack_air`
6. `rx_pcb_coil`

## Pre-Unite Copper Segment Order
1. `rx_copper_wall_t0..t{N-1}`
2. `rx_copper_coil_t0..t{N-1}`
3. `rx_bridge_s0..s{2N-2}`
4. `rx_stub_in`
5. `rx_stub_out`

이 labels는 geometry provenance와 `stub_port` metadata source로만 남는다. final exported handoff list는
`rx_plate_copper`, `rx_pcb_wall`, `rx_stack_pet_psa`, `rx_stack_ferrite`, `rx_stack_air`, `rx_pcb_coil`만 허용한다.
legacy `rx_*_uN` 분할 라벨은 final body list에 남아 있으면 안 된다.

## Ferrite And Copper Groups
- flat body order와 별개로, copper body는 단일 `g_copper_rx` group으로 export/import 재생성된다.
  - member: `rx_plate_copper`
- ferrite-family bodies는 단일 `g_ferrite_rx` group으로 export/import 재생성된다.
  - `rx_stack_pet_psa`
  - `rx_stack_ferrite`
  - `rx_stack_air`
- AEDT import-only path는 STEP hierarchy를 직접 신뢰하지 않는다.
  imported flat body names와 ledger `expected_exported_body_groups`를 사용해
  styling 직후 `create_group("g_copper_rx")`와 `create_group("g_ferrite_rx")`로 같은 groups를 재생성한다.

## Export Metadata
- `expected_exported_body_count`는 exact-name list 길이로 결정된다.
- current fixed RX baseline (`pcb_total_thickness_mm = 0.4`, `turn_count = 3`)는 final `6` bodies다.
  TX fixed baseline도 같은 `pcb_total_thickness_mm = 0.4`를 사용한다.
- `expected_exported_body_groups`는 `g_copper_rx`와 `g_ferrite_rx` groups를 가진다.
- `canonical_coordinates.pcb_layer_z_positions_mm`는 wall/coil-side PCB 시작 X 두 개를 가진다.
- `canonical_coordinates.copper_layer_z_positions_mm`는 wall/coil-side copper 시작 X 두 개를 가진다.
- `terminal_metadata.kind = "stub_port"`를 쓰고, `port_sheet_vertices_xyz`는 `rx_plate_port_sheet`
  reconstruct용 metadata-only rectangle이다. stub rectangle의 `z` span은 full-height conductor layout에서
  계산된 `rx_stub_in/out` bounds를 그대로 따르며 sheet plane은 owner `min_y - 5.0 mm`다.
- `terminal_metadata.input_stub_body_name` / `output_stub_body_name`은 final imported body names가 아니라
  pre-unite source stub labels다.
