---
title: debug_view_0_3_0_ssw.py
created: 2026-06-07
updated: 2026-06-07
tags:
  - sdd
  - code
  - debug
---

# debug_view_0_3_0_ssw.py

- Path: `entry/debug_view_0_3_0_ssw.py`
- Responsibility: provide the VS Code F5 debug entrypoint that generates `examples/0.3.0_fixed.toml` TX/RX SSW geometry, sends it to OCP CAD Viewer, and optionally builds an AEDT port-assignment debug project when `ANSYS` is true.
- Inputs: `examples/0.3.0_fixed.toml`.
- Outputs: generated STEP artifacts, `coil_making_token.toml`, an OCP CAD Viewer `show(...)` call, optional `ssw_scene_with_ports.step`, optional AEDT port ledger/imported ledger/AEDT project, and a printed JSON summary with source, STEP path, token path, ledger path, body names, copper body names, ferrite body names, and AEDT port results.
- Canonical state: `run/ssw_0_3_0_fixed/coil_making_token.toml`, `run/ssw_0_3_0_fixed/ssw_scene.step`, `run/ssw_0_3_0_fixed/ssw_step_ledger.json`, and, when `ANSYS` is true, `run/ssw_0_3_0_fixed/ssw_scene_with_ports.step`, `ssw_aedt_port_ledger.json`, `ssw_aedt_imported_ledger.json`, and `ssw_0_3_0_ports.aedt`.
- Invariants: AEDT is launched only when `ANSYS` is explicitly true, F5 displays the generated SSW assembly rather than the old minimal two-port placeholder, and the ANSYS path creates exactly one TX terminal port and one RX terminal port before saving the project.
- Fail-fast points: failed TOML load, failed token TOML generation, failed geometry export, missing STEP file, missing token file, missing ledger file, failed port STEP export, missing AEDT port sheet names, failed AEDT import, failed lumped-port assignment, failed project save, failed STEP import, or unavailable OCP viewer connection.
- Collaborators: [ssw_step.py](../src/peetsfea/ssw_step.py.md), [ssw_ports.py](../src/peetsfea/backend/pyaedt/ssw_ports.py.md).
- Related tests: launched through VS Code task replay plus `tests/test_ssw_step.py`.
- Change hazards: preserve `cwd=${workspaceFolder}/run` launch behavior and keep `.vscode/launch.json` pointed at this entrypoint.
- Related plan: [0.3.0 ssw fixed ocp viewer](../../plans/0.3.0-ssw-fixed-ocp-viewer.md).
