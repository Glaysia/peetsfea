---
title: ssw_ports.py
created: 2026-06-08
updated: 2026-06-08
tags:
  - sdd
  - code
  - pyaedt
---

# ssw_ports.py

- Path: `src/peetsfea/backend/pyaedt/ssw_ports.py`
- Responsibility: import an SSW AEDT-port STEP ledger into HFSS, apply the recorded 0.3.0 mesh/setup/sweep payloads, and create the two terminal lumped ports required for the SSW debug path.
- Inputs: an SSW AEDT port ledger with body names, copper body names, non-model/ferrite names, and TX/RX copper-edge selection rules.
- Outputs: an AEDT project saved after STEP import, explicit material assignment for every ledger body, non-model state assignment, visual state assignment, recorded `Length1` mesh, recorded `Setup1`/`Sweep`, direct edge-based lumped-port calls, and terminal excitations `1_T1` and `2_T1`.
- Canonical state: the port ledger JSON, imported ledger JSON, AEDT object names, mesh/setup/sweep summaries, and HFSS excitation names after `AssignLumpedPort`.
- Invariants: imported STEP object names must cover every ledger body, every body must have its ledger material assigned through `Hfss.assign_material()`, repository-owned `fr4` is created/configured before assignment, semantic `mull_ferrite` ledger entries are assigned as the 0.2.25 dataset-backed `MULL12060ferrite` material, non-model objects are set non-model, ferrite sheet objects must stay model objects with ferrite material, mesh uses recorded targets `rx_ssw_coil_coil_copper` then `tx_ssw_coil_ssw_copper` with `MaxLength=1mm` and `NumMaxElem=50000`, setup/sweep use the recorded `run/mesh_analysis.py` payload values, port edge specs must contain exactly one `tx` and one `rx` role, RX normal/spiral edge specs target the X-min back face, each edge-selection rule must resolve exactly two existing copper edges, and port assignment must create `1_T1` and `2_T1`.
- Fail-fast points: missing ledger keys, invalid string lists, duplicate or missing port-edge roles, failed STEP import, missing imported objects, failed material lookup/assignment/readback, failed visual assignment, failed non-model state assignment, missing recorded mesh target, failed `AssignLengthOp`, failed `InsertSetup`, failed `InsertFrequencySweep`, unresolved copper edges, failed `AssignLumpedPort`, missing excitation names, failed project save, or failed desktop release.
- Collaborators: [debug_view_0_3_0_ssw.py](../../../../entry/debug_view_0_3_0_ssw.py.md), [proxies.py](../../aedt/proxies.py.md), [protocols.py](../../aedt/protocols.py.md).
- Tests: [test_ssw_ports.py](../../../../tests/backend_em/test_ssw_ports.py.md).
- Change hazards: do not add solve/report/radiation side effects to this debug path, do not create sheet geometry for SSW ports, do not silently skip unresolved copper edges, do not replace the 0.2.25 `MULL12060ferrite` dataset material with a constant-mu placeholder, and do not substitute minimal two-port placeholder geometry for the SSW scene.
