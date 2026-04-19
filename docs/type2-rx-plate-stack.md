---
title: type2-rx-plate-stack
created: 2026-04-19 @ 18:05
updated: 2026-04-19 @ 23:40
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
- plate-stack mesh owner는 conductor-only exact set이며 imported exact-name order의 copper family 전체다.
  - `*_copper_wall_t*`
  - `*_copper_coil_t*`
  - `*_bridge_s*`
  - `*_stub_in`
  - `*_stub_out`
- underlay solids, `*_pcb_wall`/`*_pcb_coil`, reconstructed port sheet는 mesh 대상이 아니다.
- `build_type2_em_input()`는 plate-stack exact pair를 reject하지 않고 `EmPipelineInput`을 조립한다.
- active example baseline에서 `pcb_total_thickness_mm`는 RX/TX 모두 `0.4 mm`다.
  legacy `1.6/0.4` split guidance는 active plate-stack contract가 아니다.

## 목적
- `rx_region_max` full `YZ` footprint를 그대로 쓰는 넓은 RX copper/PCB stack을 만든다.
- RX는 더 이상 `tx_rect_void` coil bridge를 통과하지 않는다.
- RX ferrite family는 effective-thickness collapse가 아니라 literal 10-set solid taxonomy를 쓴다.

## TOML 계약
- `object_id = "rx_plate_stack"`
- `role = "rx_plate_stack"`
- `material = "composite"`
- `model_state = true`
- `pcb_total_thickness_mm > copper_thickness_mm > 0`
- `ferrite_set_count = 10`
- `turn_count`는 정수 range고 realized 값은 `>= 2`여야 한다.
- `metal_fill_factor`는 float range고 realized 값은 `> 0`, `<= 0.5`여야 한다.
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
- `pitch_z = rx_region_max.size_z / N`
- wall-side stripe `t{i}`는 `z_min + i * pitch_z`에서 시작한다.
- coil-side stripe `t{i}`는 `z_min + pitch_z / 2 + i * pitch_z`에서 시작한다.
- coil-side stripe count는 `N - 1`개다.
- side bridge `rx_bridge_s*`는 `Y=max/min`을 번갈아 쓰며
  `wall_t0 -> coil_t0 -> wall_t1 -> ... -> coil_t{N-2} -> wall_t{N-1}`를 잇는다.
- terminal stub `rx_stub_in`, `rx_stub_out`는 wall-side `t0`, `t{N-1}`에 붙고 `+Y` 방향으로 `5.0 mm` 돌출한다.
- total thickness guard:
  - `2 * pcb_total_thickness_mm + 10 * (0.20 + 0.15 + 0.02) <= rx_region_max.size_x`

## Exact Body Order
1. `rx_copper_wall_t0..t{N-1}`
2. `rx_pcb_wall`
3. `rx_stack_pet_psa_u0 -> rx_stack_ferrite_u0 -> rx_stack_vacuum_u0 -> ... -> u9`
4. `rx_pcb_coil`
5. `rx_copper_coil_t0..t{N-2}`
6. `rx_bridge_s0..s{2N-3}`
7. `rx_stub_in`
8. `rx_stub_out`

## Ferrite Family Group
- flat body order와 별개로, ferrite-family bodies는 단일 `g_ferrite_rx` group으로 export된다.
- group member는 ferrite/PET_PSA/vacuum bodies 전체이며, current creation order를 그대로 따른다.
  1. `rx_stack_pet_psa_uN`
  2. `rx_stack_ferrite_uN`
  3. `rx_stack_vacuum_uN`
- AEDT import-only path는 STEP hierarchy를 직접 신뢰하지 않는다.
  imported flat body names와 ledger `expected_exported_body_groups`를 사용해
  styling 직후 `create_group("g_ferrite_rx")`로 같은 group을 재생성한다.

## Export Metadata
- `expected_exported_body_count`는 exact-name list 길이로 결정된다.
- current fixed RX baseline (`pcb_total_thickness_mm = 0.4`, `turn_count = 3`)는 `43` bodies다.
  TX fixed baseline도 같은 `pcb_total_thickness_mm = 0.4`를 사용한다.
- `expected_exported_body_groups`는 ferrite/PET_PSA/vacuum family 전체를 creation order로 담는
  단일 `g_ferrite_rx` group을 가진다.
- `canonical_coordinates.pcb_layer_z_positions_mm`는 wall/coil-side PCB 시작 X 두 개를 가진다.
- `canonical_coordinates.copper_layer_z_positions_mm`는 wall/coil-side copper 시작 X 두 개를 가진다.
- `terminal_metadata.kind = "stub_port"`를 쓰고, `port_sheet_vertices_xyz`는 `rx_plate_port_sheet`
  reconstruct용 metadata-only rectangle이다. stub rectangle의 `z` span은 full-height conductor layout에서
  계산된 `rx_stub_in/out` bounds를 그대로 따른다.
