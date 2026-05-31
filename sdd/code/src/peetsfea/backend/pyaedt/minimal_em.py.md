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
- Inputs: minimal ledger path, output AEDT path, imported ledger path, HFSS factory.
- Outputs: setup result or solve result with `.aedt`, imported ledger, mesh, ports, sources, analysis, reports, validation, and optional CSV export.
- Canonical state: the loaded minimal ledger and imported object names validated against the HFSS modeler.
- Invariants: exactly one Tx and one Rx port sheet, fixed port slots `1` and `2`, four copper mesh targets, and required reports.
- Fail-fast points: import failure, missing imported bodies, port edge resolution failure, PyAEDT `False`, failed validation, failed save, failed solve/report export.
- Collaborators: [minimal_step.py](../../../minimal_step.py.md), existing AEDT wrappers/protocols, EM pipeline analysis/source helpers.
- Tests: `tests/backend_em/test_minimal_em.py`.
- Hazards: do not add fallback import behavior; exact minimal ledger names are the runtime contract.
- Related plan: [0.3.0 minimal step two port reset](../../../../plans/0.3.0-minimal-step-two-port-reset.md).
