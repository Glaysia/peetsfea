---
title: GOAL
created: 2026-06-01
updated: 2026-06-01
tags:
  - goal
  - 0.3.0
---

# 0.3.0 Goal

0.3.0 resets the active product path to a minimal STEP-based two-port EM baseline.

The old geometry generation surface is removed. Coil, plate-stack, rect-void, underlay, TV sheet, active type2 geometry, and legacy geometry builders are not preserved as active or legacy implementation paths. The repository keeps only the code needed to parse a non-model-only TOML, generate one minimal STEP scene, import it into HFSS, assign two ports, mesh the metal pads, create analysis/report state, and optionally solve/export the report.

## Target Contract

- `spec_version = "0.3.0"`
- `schema_id = "peetsfea.minimal_step_two_port.v1"`
- Authoring TOML contains `[design]` and `[[non_model_objects]]` only.
- The minimal STEP contains:
  - every authored non-model box
  - one Tx port cell at the scene center-left
  - one Rx port cell at the scene center-right
- Each port cell contains two copper half-pads and one vacuum port sheet.
- HFSS terminal ports are fixed:
  - Tx: `1_T1`
  - Rx: `2_T1`
- Default EM setup is headless, fail-fast, and creates mesh, radiation boundary, source phase, `Setup1`, sweep, and `Output Variables Table1`.

## Default Geometry

The default generated metal uses millimeters.

- Tx center: `[-25.0, 0.0, 0.0]`
- Rx center: `[25.0, 0.0, 0.0]`
- Copper pad cell: `20.0 x 10.0 x 0.035`
- Port gap along Y: `1.0`
- Port sheet lies in the pad gap and spans the pad X width.
- Canonical body names:
  - `tx_signal_pad`
  - `tx_reference_pad`
  - `tx_port_sheet`
  - `rx_signal_pad`
  - `rx_reference_pad`
  - `rx_port_sheet`

## Acceptance

- `entry/sample.py` writes the minimal manifest and sampled artifacts from the non-model-only example TOML.
- `entry/build.py` generates missing STEP artifacts, imports them into HFSS, creates setup-ready state, and supports `--solve`.
- Default tests do not import removed geometry modules.
- Headless AEDT validation remains opt-in through the normal build path; GUI validation is not part of this goal.
