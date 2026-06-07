---
title: minimal_em.py
created: 2026-06-01
updated: 2026-06-01
tags:
  - sdd
  - code
---

# minimal_em.py

- Path: `src/peetsfea/backend/pyaedt/minimal_em.py`
- Responsibility: import the minimal STEP ledger into HFSS and create setup-ready or solved two-port EM artifacts.
- Inputs: minimal ledger path, output AEDT path, imported ledger path, HFSS factory, and release policy.
- Outputs: setup result or solve result with `.aedt`, imported ledger, material assignments, visual assignments, mesh, ports, sources, analysis, reports, validation, and optional CSV export.
- Canonical state: the loaded minimal ledger, imported object names validated against the HFSS modeler, copper body material assignments read back from AEDT, and applied visual assignments.
- Invariants: exactly one Tx and one Rx port sheet, fixed port slots `1` and `2`, four copper mesh targets with `copper` material assigned after STEP import, restored visual state for non-model/copper/port-sheet objects, restored `2000mm` radiation region, restored type2 setup policy `MaxDeltaS=0.0017`/passes `22/20/21`/`BasisOrder=0`/`DoLambdaRefine=false`, the AEDT-compatible interpolating sweep payload shape from the prior EM pipeline, restored TxRx output variables, and required reports `Output Variables Table1`, `Table1`, and `Table2` with `Table2` primary sweep `Pass`.
- Fail-fast points: import failure, missing imported bodies, missing/invalid copper material, failed AEDT material assignment readback, missing visual-state attributes, port edge resolution failure, PyAEDT `False`, failed validation, failed save, failed solve/report export, failed desktop release when release is requested.
- Collaborators: [minimal_step.py](../../../minimal_step.py.md), existing AEDT wrappers/protocols, EM pipeline analysis/source helpers.
- Tests: `tests/backend_em/test_minimal_em.py`.
- Hazards: do not add fallback import behavior; exact minimal ledger names are the runtime contract. GUI factories must be opt-in and must not change the headless default. Do not simplify the sweep payload or report variable set without live AEDT validation.
- Related plan: [0.3.0 minimal step two port reset](../../../../plans/0.3.0-minimal-step-two-port-reset.md).
