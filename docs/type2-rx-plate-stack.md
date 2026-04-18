---
title: type2-rx-plate-stack
created: 2026-04-19 @ 18:05
updated: 2026-04-19 @ 21:20
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
geometry/export-only이며, 현재 phase에서는 HFSS import/setup-ready/EM path를 지원하지 않는다.

## Runtime Boundary
- `type2_step_setup_ready`는 `rx_plate_stack`를 HFSS work 시작 전에 reject한다.
- direct helper `assign_post_import_mesh`, `assign_type2_lumped_ports`, `build_type2_em_input`도
  `rx_plate_stack`를 명시적으로 reject한다.
- `terminal_metadata = {"kind": "none"}` sentinel은 이 runtime boundary와 맞물린 계약이다.
  current phase에서는 port-sheet reconstruction metadata를 만들지 않는다.

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
- coil-only field `outer_*`, `turn_count`, `layer_count`, `terminal_path`, `void_*`, `margin_ratio`,
  `metal_fill_factor`, `underlay_repeat_count`, `underlay_gap_mm`, `wall_parallel_stack_present`는 선언하면 안 된다.

## Geometry Contract
- placement owner는 `rx_region_max`다.
- footprint source of truth는 `rx_region_max` full `YZ` size다.
- stack는 `rx_region_max.min_x`에 붙고 `+X` 방향으로 자란다.
- `pcb_total_thickness_mm`은 copper 1 layer를 포함한 board total thickness다.
  - wall-side board: `rx_copper_wall`, `rx_pcb_wall`
  - coil-side board: `rx_pcb_coil`, `rx_copper_coil`
  - epoxy thickness는 `pcb_total_thickness_mm - copper_thickness_mm`
- ferrite/PET/air set는 literal 10회로 export된다.
  - ferrite `0.20 mm`
  - PET/PSA `0.15 mm`
  - air `0.02 mm`
- total thickness guard:
  - `2 * pcb_total_thickness_mm + 10 * (0.20 + 0.15 + 0.02) <= rx_region_max.size_x`

## Exact Body Order
1. `rx_copper_wall`
2. `rx_pcb_wall`
3. `rx_stack_ferrite_u0` .. `rx_stack_ferrite_u9`
4. `rx_stack_pet_psa_u0` .. `rx_stack_pet_psa_u9`
5. `rx_stack_air_u0` .. `rx_stack_air_u9`
6. `rx_pcb_coil`
7. `rx_copper_coil`

## Export Metadata
- `expected_exported_body_count = 34`
- `canonical_coordinates.pcb_layer_z_positions_mm`는 wall/coil-side PCB 시작 X 두 개를 가진다.
- `canonical_coordinates.copper_layer_z_positions_mm`는 wall/coil-side copper 시작 X 두 개를 가진다.
- `terminal_metadata = {"kind": "none"}` sentinel을 쓴다.
- port-sheet metadata는 없다.
