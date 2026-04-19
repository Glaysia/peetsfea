---
title: type2-plate-stack
created: 2026-04-19 @ 21:20
updated: 2026-04-20 @ 00:45
tags:
  - type2
  - tx
  - rx
  - plate-stack
  - hfss
---

# Type2 Plate Stack

이 문서는 active type2 plate-stack family의 shared runtime boundary를 설명한다.
`tx_plate_stack`, `rx_plate_stack`는 scene/STEP ledger 단계의 modeled object role이며,
current flow는 setup-ready full-EM-ready build path를 포함한다. import-only helper는 geometry inspection /
import-only surface다. active example baseline에서 TX/RX PCB total thickness는 둘 다 `0.4 mm`다.

## Shared Contract
- plate-stack roles: `tx_plate_stack`, `rx_plate_stack`
- TX/RX plate-stack generation ownership은 shared contract/runtime path 하나가 가진다.
  RX-specific 문서는 role-local detail reference이며 canonical owner가 아니다.
- plate-stack entries는 coil terminal reconstruction owner가 아니라 geometry/export owner다.
- active geometry/export contract가 읽는 plate-stack field set은 `pcb_total_thickness_mm`,
  `copper_thickness_mm`, `ferrite_set_count`, `turn_count`, `metal_fill_factor`다.
- active example PCB total thickness baseline은 TX/RX 모두 `pcb_total_thickness_mm = 0.4`다.
  legacy `1.6/0.4` split guidance는 active plate-stack contract가 아니다.
- `shoe_depth_mm`는 active type2 plate-stack public field가 아니다. plate-stack modeled object에
  남아 있으면 loader가 removed field로 즉시 실패한다.
- `turn_count`는 wall-side copper turn owner다. coil-side copper는 항상 `turn_count - 1`이다.
- active plate-stack exact order는 wall-side striped copper `*_copper_wall_t*`, `*_pcb_wall`,
  interleaved `PET/PSA -> ferrite -> air` stack sets, `*_pcb_coil`, coil-side striped copper
  `*_copper_coil_t*`, side bridge `*_bridge_s*`, terminal stub `*_stub_in/out` 순서다.
- plate-stack ferrite-family STEP export contract는 per-set `*_uN` exact body가 아니라
  per-material merged exact body다.
  - TX exact body names: `tx_stack_pet_psa`, `tx_stack_ferrite`, `tx_stack_air`
  - RX exact body names: `rx_stack_pet_psa`, `rx_stack_ferrite`, `rx_stack_air`
  - role당 ferrite-family STEP exact bodies는 정확히 3개다.
- `expected_exported_body_groups`의 `g_ferrite_tx`, `g_ferrite_rx`는 flattened per-set member가 아니라
  위 merged 3-body exact names를 reference한다.
- per-set `*_stack_sandwich_uN` group과 old `*_u0..u9` plate-stack exact-name contract는 active path가 아니다.
- striped copper는 full owner `Z` height를 `turn_count`로 나눈 `pitch_z`를 기준으로 하고,
  `trace_height_z = pitch_z * metal_fill_factor`, `stripe_center_offset_z = (pitch_z - trace_height_z) / 2`를 사용한다.
- wall/coil stripe는 각 pitch slot lower-bound에 바로 붙지 않고 slot 중심으로 정렬된다.
- active contract에서 `metal_fill_factor`는 `0 < fill <= 0.6`을 허용한다.
- bridge `*_bridge_s*`는 serpentine `Y=max/min` alternation을 유지하면서,
  owner `Z` bounds clip + same-edge non-overlap clip을 함께 적용해 high fill에서도
  bridge/slab positive-volume overlap과 same-edge neighboring bridge overlap을 만들지 않는다.
- terminal metadata는 sentinel `{"kind": "none"}`가 아니라 아래 `stub_port` contract다.
  - `kind = "stub_port"`
  - `input_stub_body_name`
  - `output_stub_body_name`
  - `start_point_plane_mm`
  - `end_point_plane_mm`
  - `port_sheet_vertices_xyz`
- plate-stack roles는 port-sheet STEP body를 export하지 않는다. port sheet는 metadata-only helper다.

## HFSS Runtime Boundary
- `peetsfea.backend.pyaedt.type2_step_setup_ready`의 active default build path는 plate-stack exact pair를
  setup-ready full-EM-ready branch로 처리한다.
- setup-ready facade는 plate-stack exact pair에서도 아래 후반부를 동일 실행한다.
  - post-import mesh
  - radiation boundary
  - explicit lumped ports
  - source phase
  - analysis/report
  - `validate_pipeline()`
  - `ValidateDesign()`
  - final save
- import-only AEDT path는 STEP hierarchy preservation을 직접 신뢰하지 않고, styled flat bodies와
  ledger metadata를 사용해 merged ferrite-family exact bodies (`*_stack_pet_psa`, `*_stack_ferrite`,
  `*_stack_air`)를 role별 단일 group (`g_ferrite_tx`, `g_ferrite_rx`)으로 연결하고
  `tx_plate_port_sheet` / `rx_plate_port_sheet`
  metadata-only sheet를 추가로 reconstruct한다.
- plate-stack port contract는 reconstructed `tx_plate_port_sheet` / `rx_plate_port_sheet`를 사용하고,
  numeric naming은 TX `1/1_T1`, RX `2/2_T1`다.
- plate-stack mesh owner는 conductor-only exact set이며 imported exact-name order의 copper family 전체다.
  - `*_copper_wall_t*`
  - `*_copper_coil_t*`
  - `*_bridge_s*`
  - `*_stub_in`
  - `*_stub_out`
- underlay solids, `*_pcb_wall`/`*_pcb_coil`, reconstructed `tx_plate_port_sheet`/`rx_plate_port_sheet`는 mesh 대상이 아니다.
- `build_type2_em_input()`는 plate-stack exact pair를 reject하지 않고 `EmPipelineInput`을 조립한다.

## Role Notes
- `tx_plate_stack`: active TX plate-stack는 `tx_region` full `YZ` footprint를 쓰고
  `tx_region.min_x`에 붙어 `+X` 방향으로 쌓인다. wall/coil-side striped copper는 full owner `Z`
  height를 공유하고, terminal stub는 wall-side `t0`, `t{N-1}`에서 `+Y`로 `5.0 mm` 돌출한다.
- `rx_plate_stack`: active RX plate-stack는 `rx_region_max` full `YZ` footprint를 쓰고
  `rx_region_max.min_x`에 붙어 `+X` 방향으로 쌓인다. wall/coil-side striped copper는 full owner `Z`
  height를 공유하고, terminal stub는 같은 규칙으로 wall-side `t0`, `t{N-1}`에서 `+Y`로 돌출한다.

## Legacy Coil Reference
- `tx_single_coil` / legacy `rx_single_coil` coil geometry reference는
  [`docs/tx-rect-void-step.md`](tx-rect-void-step.md)에 남아 있다.
- 그 문서는 legacy coil contract용이며, active TX/RX plate-stack contract 문서가 아니다.
