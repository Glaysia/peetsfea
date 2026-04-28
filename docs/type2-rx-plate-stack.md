---
title: type2-rx-plate-stack
created: 2026-04-19 @ 18:05
updated: 2026-04-28 @ 00:00
tags:
  - type2
  - rx
  - plate-stack
  - step-export
---

# Type2 RX Plate Stack

이 문서는 RX role-local plate-stack reference다.
Active type2 setup-ready 기본 경로는 RxOnly이며, 이 문서는 송신 형상이나 paired setup 계약을 정의하지 않는다.

## Runtime Boundary
- RX plate-stack metadata may feed RxOnly setup when the active RX path selects it.
- Setup-ready owns RX mesh, radiation boundary, one RX lumped port, RX source phase, RX analysis/report, validation, and final save.
- RX port sheet is reconstructed runtime geometry, not a STEP body.
- Mesh ownership is RX conductor-only.
- Non-conductor context bodies and reconstructed sheets are not mesh targets.

## TOML Contract
- `object_id = "rx_plate_stack"`
- `role = "rx_plate_stack"`
- `material = "composite"`
- `model_state = true`
- `pcb_total_thickness_mm > copper_thickness_mm > 0`
- `turn_count` realized value must be `>= 2`.
- `metal_fill_factor` realized value must be `> 0` and `<= 0.6`.
- `z_usage_ratio` realized value must be `> 0` and `<= 1`.
- `y_usage_ratio` realized value must be `> 0` and `<= 1`.
- Removed or coil-only fields must fail immediately when declared on the RX plate-stack object.

## Geometry Contract
- Placement owner is `rx_region_max`.
- RX active Y window is centered on global `Y=0`.
- RX active Z window starts from the bottom of `rx_region_max`.
- RX copper provenance labels are pre-unite metadata only.
- Final RX conductor handoff is one united RX conductor body.
- RX ferrite-family bodies are equivalent material slabs, not per-set repeated public fields.

## Export Metadata
- `expected_exported_body_count` is derived from the final exact-name list.
- RX terminal metadata uses `kind = "stub_port"`.
- `port_sheet_vertices_xyz` is metadata for RX runtime reconstruction.
- Import-only recreates RX ownership from ledger metadata and does not create setup-ready state.
