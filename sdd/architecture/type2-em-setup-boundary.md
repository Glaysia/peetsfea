---
title: Type2 EM Setup Boundary
created: 2026-05-03 @ 00:00
updated: 2026-05-03 @ 00:00
tags:
  - em
  - pyaedt
  - sdd
---

# Type2 EM Setup Boundary

This note owns the graph cluster for turning imported type2 geometry into setup-ready or solve-ready HFSS projects.

## Boundary Role
- Reuse the STEP import boundary, then apply mesh, radiation boundary, lumped ports, sources, analysis setup, report variables, validation, save, and optional solve/export.
- Keep `RxOnly` and `TxRx` active-mode rules explicit.
- Keep geometry-only `tx_outer_single_coil` import/styling separate from active EM setup inputs.

## Owned Code Notes
- [setup_type2_step.py](../code/entry/setup_type2_step.py.md)
- [type2_step_setup_ready.py](../code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py.md)
- [type2_step_post_import_mesh.py](../code/src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py.md)
- [type2_step_em_input.py](../code/src/peetsfea/backend/pyaedt/type2_step_em_input.py.md)
- [type2_step_port_assignment.py](../code/src/peetsfea/backend/pyaedt/type2_step_port_assignment.py.md)
- [type2_step_em_solve.py](../code/src/peetsfea/backend/pyaedt/type2_step_em_solve.py.md)

## Exceptional Handoffs
- Import-only geometry and imported ledger creation are owned by [type2-step-import-boundary](type2-step-import-boundary.md).
- Raw HFSS/session access is owned by [pyaedt-boundary](pyaedt-boundary.md).
- Report variable shape is owned by [type2-em-report-contract](type2-em-report-contract.md).

## Graph Intent
- This node is intentionally high-degree because it owns the active EM handoff from imported geometry to validated `.aedt` and optional report CSV artifacts.
- Direct helper links should show the setup chain: setup-ready to mesh/input/port/solve, EM input to report contract, solve to runtime/report export.
