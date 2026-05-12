---
title: type2_single_coil_ports.py
created: 2026-04-20 @ 00:00
updated: 2026-05-13 @ 00:00
tags:
  - rx
  - ports
---

# type2_single_coil_ports.py

## Source
- Path: `src/peetsfea/type2_single_coil_ports.py`
- Code note path: `sdd/code/src/peetsfea/type2_single_coil_ports.py.md`
- Status: active

## 역할
- Active Type2 single-coil port contract resolver다.
- STEP generation time에 terminal stub boxes에서 global-mm sheet vertices and integration-line endpoints를 계산한다.
- Sampled TOML이나 AEDT-imported geometry에서 port coordinates를 역산하지 않는다.

## 입력 / 출력
- 입력: realized terminal path, centerline, `SingleCoilProfile`, frame origin, transformed terminal/copper boxes
- 출력: `kind = "single_coil_port_v1"` terminal metadata with `sheet_name`, `vertices_xyz`, `integration_line_start_xyz`, and `integration_line_end_xyz`

## Canonical state
- The terminal metadata written to `type2_step_ledger.json` is the canonical resolved port sheet state.
- Sheet vertices are ordered so vertices `[3] -> [0]` are the signal edge and `[1] -> [2]` are the reference edge.

## Invariants / fail-fast
- Missing, ambiguous, unbalanced, non-finite, or degenerate terminal stub geometry fails immediately.
- TX parallel single-coil ports use synthetic bus owner boxes built from balanced start/end terminal stub columns.
- RX single-coil ports require exactly one start and one end terminal stub box.

## Collaborators
- [type2_step_port_assignment.py](backend/pyaedt/type2_step_port_assignment.py.md)
- [type2_single_coil_scene.py](type2_single_coil_scene.py.md)
- [0.2.25 Type2 Port Sheet Contract Rewrite](../../../plans/0.2.25-type2-port-sheet-contract-rewrite.md)
