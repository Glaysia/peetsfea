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
- Responsibility: verify the SSW AEDT import, material, recorded mesh/boundary/setup/sweep, port, and restored report contract with both fake-session contract tests and a real headless AEDT integration test.
- Inputs: generated fake SSW port ledgers, a fake HFSS session, generated 0.3.0 SSW AEDT port artifacts, and a real headless HFSS session for the `pyaedt_integration` case.
- Outputs: pytest assertions for STEP import kwargs, explicit all-body material assignment, non-model model-state changes, ferrite model-state preservation, visual assignments, recorded mesh/setup/sweep payloads, `Region_Abs_2000mm` radiation payloads, direct edge-based lumped-port payloads, output-variable creation, report payloads, saved AEDT path, imported ledger content, desktop release behavior, fail-fast AEDT operation failures, and real headless AEDT creation of `1_T1`/`2_T1`.
- Canonical state: the fake ledger body names, TX/RX semantic port edge endpoint pairs, fake mesh/boundary/setup/report call records, fake output variables, fake modeler edge IDs and endpoint coordinates, fake boundary excitations, real imported ledger, saved `.aedt` path, and result `ports`/`boundary`/`reports` mapping.
- Invariants: exactly two port edge specs are required, each port edge spec stores exactly two semantic endpoint pairs, material assignment covers every ledger body including vacuum, copper, FR4, and ferrite roles, semantic ferrite entries are assigned as 0.2.25 `MULL12060ferrite` through dataset import/project material definition/material lookup sync, recorded mesh targets and `Setup1`/`Sweep` payload values are preserved, radiation boundary generation creates `Region_Abs_2000mm` and six `Rad_RegionAbs_*` face boundaries, semantic endpoint pairs match imported copper edges before `AssignLumpedPort`, `AssignLumpedPort` creates `1_T1` and `2_T1`, restored Tx/Rx output variables are created against `Setup1 : Sweep`, reports `Output Variables Table1`, `Table1`, and `Table2` are registered, imported ledger content mirrors the setup result, PyAEDT `False` returns raise instead of logging and continuing, and the integration-marked test must launch real headless AEDT rather than a fake session.
- Fail-fast points: failed `AssignLengthOp`, `create_region`, missing six region faces, `assign_radiation_boundary_to_faces`, `InsertSetup`, `InsertFrequencySweep`, `AssignLumpedPort`, output-variable creation, `CreateReport`, missing report registration, missing imported bodies, unresolved semantic copper edge endpoints, failed desktop release, failed headless AEDT startup, failed STEP import, missing excitations, or failed project save.
- Collaborators: [ssw_ports.py](../../src/peetsfea/backend/pyaedt/ssw_ports.py.md).
