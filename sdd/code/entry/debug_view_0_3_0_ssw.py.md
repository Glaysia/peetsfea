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
- Responsibility: provide the VS Code F5 debug entrypoint that generates `examples/0.3.0_fixed.toml` TX/RX SSW geometry and sends it to OCP CAD Viewer.
- Inputs: `examples/0.3.0_fixed.toml`.
- Outputs: generated STEP artifacts, `coil_making_token.toml`, an OCP CAD Viewer `show(...)` call, and a printed JSON summary with source, STEP path, token path, ledger path, body names, and copper body names.
- Canonical state: `run/ssw_0_3_0_fixed/coil_making_token.toml`, `run/ssw_0_3_0_fixed/ssw_scene.step`, and `run/ssw_0_3_0_fixed/ssw_step_ledger.json`.
- Invariants: the entrypoint never launches AEDT GUI, and F5 displays the generated SSW assembly rather than the old minimal two-port placeholder.
- Fail-fast points: failed TOML load, failed token TOML generation, failed geometry export, missing STEP file, missing token file, missing ledger file, failed STEP import, or unavailable OCP viewer connection.
- Collaborators: [ssw_step.py](../src/peetsfea/ssw_step.py.md).
- Related tests: launched through VS Code task replay plus `tests/test_ssw_step.py`.
- Change hazards: preserve `cwd=${workspaceFolder}/run` launch behavior and keep `.vscode/launch.json` pointed at this entrypoint.
- Related plan: [0.3.0 ssw fixed ocp viewer](../../plans/0.3.0-ssw-fixed-ocp-viewer.md).
