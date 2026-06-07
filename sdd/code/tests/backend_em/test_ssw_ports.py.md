---
title: test_ssw_ports.py
created: 2026-06-08
updated: 2026-06-08
tags:
  - sdd
  - code
  - test
---

# test_ssw_ports.py

- Path: `tests/backend_em/test_ssw_ports.py`
- Responsibility: verify the SSW AEDT port-only import/setup contract with both fake-session contract tests and a real headless AEDT integration test.
- Inputs: generated fake SSW port ledgers, a fake HFSS session, generated 0.3.0 SSW AEDT port artifacts, and a real headless HFSS session for the `pyaedt_integration` case.
- Outputs: pytest assertions for STEP import kwargs, copper material assignment, non-model/ferrite model-state changes, visual assignments, lumped-port payloads, saved AEDT path, imported ledger content, desktop release behavior, fail-fast port assignment failure, and real headless AEDT creation of `1_T1`/`2_T1`.
- Canonical state: the fake ledger body names, TX/RX port cells, fake modeler edge IDs, fake boundary excitations, real imported ledger, saved `.aedt` path, and result `ports` mapping.
- Invariants: exactly two port cells are required, `AssignLumpedPort` creates `1_T1` and `2_T1`, imported ledger content mirrors the setup result, PyAEDT `False` returns raise instead of logging and continuing, and the integration-marked test must launch real headless AEDT rather than a fake session.
- Fail-fast points: failed `AssignLumpedPort`, missing imported bodies, missing sheet edges, failed desktop release, failed headless AEDT startup, failed STEP import, missing excitations, or failed project save.
- Collaborators: [ssw_ports.py](../../src/peetsfea/backend/pyaedt/ssw_ports.py.md).
