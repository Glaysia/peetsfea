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
- Responsibility: import an SSW AEDT-port STEP ledger into HFSS and create the two terminal lumped ports required for the 0.3.0 SSW debug path.
- Inputs: an SSW AEDT port ledger with body names, copper body names, non-model/ferrite names, and TX/RX copper-edge selection rules.
- Outputs: an AEDT project saved after STEP import, copper material assignment, non-model state assignment, visual state assignment, direct edge-based lumped-port calls, and terminal excitations `1_T1` and `2_T1`.
- Canonical state: the port ledger JSON, imported ledger JSON, AEDT object names, and HFSS excitation names after `AssignLumpedPort`.
- Invariants: imported STEP object names must cover every ledger body, copper bodies must have copper material entries, non-model/ferrite objects are set non-model, port edge specs must contain exactly one `tx` and one `rx` role, RX normal/spiral edge specs target the X-min back face, each edge-selection rule must resolve exactly two existing copper edges, and port assignment must create `1_T1` and `2_T1`.
- Fail-fast points: missing ledger keys, invalid string lists, duplicate or missing port-edge roles, failed STEP import, missing imported objects, failed material lookup/assignment, failed visual assignment, failed non-model state assignment, unresolved copper edges, failed `AssignLumpedPort`, missing excitation names, failed project save, or failed desktop release.
- Collaborators: [debug_view_0_3_0_ssw.py](../../../../entry/debug_view_0_3_0_ssw.py.md), [proxies.py](../../aedt/proxies.py.md), [protocols.py](../../aedt/protocols.py.md).
- Tests: [test_ssw_ports.py](../../../../tests/backend_em/test_ssw_ports.py.md).
- Change hazards: do not add mesh/solve/report side effects to this port-only debug path, do not create sheet geometry for SSW ports, do not silently skip unresolved copper edges, and do not substitute minimal two-port placeholder geometry for the SSW scene.
