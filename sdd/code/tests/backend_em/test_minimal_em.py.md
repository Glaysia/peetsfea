---
title: test_minimal_em.py
created: 2026-06-01
updated: 2026-06-01
tags:
  - sdd
  - code
---

# test_minimal_em.py

- Path: `tests/backend_em/test_minimal_em.py`
- Responsibility: verify the fake-HFSS minimal EM setup/solve contract and desktop release policy.
- Inputs: generated minimal ledgers and fake HFSS sessions.
- Outputs: assertions for import, copper material assignment, visual state assignment, mesh, port, restored setup policy, AEDT-compatible sweep payload, analysis, report, save, solve, and release calls.
- Canonical state: fake session call records.
- Invariants: Tx/Rx port names, copper body material readback, restored object colors/transparency, restored `3500mm` radiation region, setup policy `0.0017`/`22/20/21`/`BasisOrder=0`/lambda-refine off, mesh targets, restored TxRx report variables, and diagnostic report surfaces stay fixed with `Table2` X component `Pass`; setup closes AEDT by default but can leave a GUI session open when explicitly requested.
- Fail-fast points: PyAEDT-style false returns, missing required bodies, and missing AEDT materials.
- Collaborators: [minimal_em.py](../../src/peetsfea/backend/pyaedt/minimal_em.py.md).
- Tests: this file.
- Hazards: fake behavior must model required boundary calls only.
- Related plan: [0.3.0 minimal step two port reset](../../plans/0.3.0-minimal-step-two-port-reset.md).
