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
- Responsibility: verify the fake-HFSS minimal EM setup/solve contract.
- Inputs: generated minimal ledgers and fake HFSS sessions.
- Outputs: assertions for import, mesh, port, analysis, report, save, and solve calls.
- Canonical state: fake session call records.
- Invariants: Tx/Rx port names and mesh targets stay fixed.
- Fail-fast points: PyAEDT-style false returns and missing required bodies.
- Collaborators: [minimal_em.py](../../src/peetsfea/backend/pyaedt/minimal_em.py.md).
- Tests: this file.
- Hazards: fake behavior must model required boundary calls only.
- Related plan: [0.3.0 minimal step two port reset](../../plans/0.3.0-minimal-step-two-port-reset.md).
