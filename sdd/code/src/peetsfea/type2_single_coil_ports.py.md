---
title: type2_single_coil_ports.py
created: 2026-04-20 @ 00:00
updated: 2026-05-21 @ 00:00
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
- STEP generation time에 realized single-coil terminal quarter-turn metadata와 terminal stub boxes에서 global-mm sheet vertices and integration-line endpoints를 계산한다.
- Sampled TOML이나 AEDT-imported geometry에서 port coordinates를 역산하지 않는다.

## 입력 / 출력
- 입력: realized `terminal_start`/`turn_qcount`, `SingleCoilProfile`, frame origin, transformed terminal/copper boxes
- 출력: `kind = "single_coil_port_v1"` terminal metadata with `path`, `outer_corner`, `inner_corner`, fixed `direction = "cw"`, `sheet_name`, `vertices_xyz`, `integration_line_start_xyz`, and `integration_line_end_xyz`

## Canonical state
- The terminal metadata written to `type2_step_ledger.json` is the canonical resolved port sheet state.
- Compatibility terminal fields are consumed from and validated against the realized core contract: `terminal_path`, `terminal_start`, `terminal_start_corner`, `terminal_end_corner`, `terminal_direction`, and `turn_qcount` must agree before metadata is emitted.
- `terminal_start` maps `0..3` to `A/B/C/D`, `inner_corner` maps `(terminal_start + turn_qcount) % 4` to `a/b/c/d`, and `path` is the realized `<outer>_cw_to_<inner>` path.
- Sheet vertices are ordered so vertices `[3] -> [0]` are the signal edge and `[1] -> [2]` are the reference edge.
- The four sheet vertices must also form a simple non-self-intersecting loop for AEDT `CreatePolyline`; the reference edge order is chosen so the loop does not become a bow-tie while preserving the signal/reference edge indices used by integration-line metadata.

## Invariants / fail-fast
- Missing, ambiguous, unbalanced, non-finite, or degenerate terminal stub geometry fails immediately.
- Missing or invalid realized `terminal_start` / `turn_qcount` fails immediately; the scene must not read TOML-owned `terminal_path` to populate active single-coil port metadata.
- Self-intersecting port-sheet vertex ordering is forbidden because AEDT rejects it at `CreatePolyline`.
- TX parallel single-coil ports use synthetic bus owner boxes built from balanced start/end terminal stub columns.
- RX single-coil ports require exactly one start and one end terminal stub box.

## Collaborators
- [type2_step_port_assignment.py](backend/pyaedt/type2_step_port_assignment.py.md)
- [type2_single_coil_scene.py](type2_single_coil_scene.py.md)
- [0.2.25 Type2 Port Sheet Contract Rewrite](../../../plans/0.2.25-type2-port-sheet-contract-rewrite.md)
