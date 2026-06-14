---
title: debug_view_0_3_0_ssw.py
created: 2026-06-07
updated: 2026-06-10
tags:
  - sdd
  - code
  - debug
---

# debug_view_0_3_0_ssw.py

- Path: `entry/debug_view_0_3_0_ssw.py`
- Responsibility: provide the VS Code F5 debug entrypoint that generates `examples/0.3.0_fixed.toml` TX/RX SSW geometry, sends it to OCP CAD Viewer, and optionally builds an AEDT port-assignment debug project when `ANSYS` is true.
- Inputs: `examples/0.3.0_fixed.toml`.
- Outputs: generated STEP artifacts, `coil_making_token.toml`, an OCP CAD Viewer `show(...)` call, optional AEDT port ledger/imported ledger/AEDT project, PeetsFEA timing logs for the launch entry and the first three high-level call-stack levels, and a printed JSON summary with source, STEP path, token path, ledger path, semantic body names, short AEDT identity fields, and AEDT port results.
- Canonical state: `run/ssw_0_3_0_fixed/coil_making_token.toml`, `run/ssw_0_3_0_fixed/ssw_scene.step`, `run/ssw_0_3_0_fixed/ssw_step_ledger.json`, and, when `ANSYS` is true, `ssw_aedt_port_ledger.json`, `ssw_aedt_imported_ledger.json`, and a point-derived `0_3_0_p*.aedt` file.
- Invariants: AEDT is launched only when `ANSYS` is explicitly true, F5 displays the generated SSW assembly rather than the old minimal two-port placeholder, timing decorators stay limited to `main()`, `show_ssw_fixed_in_ocp()`, `setup_ansys_ports_for_ssw_debug()`, `generate_ssw_debug_summary()`, and `export_ssw_aedt_port_artifacts()` for the launch stack, AEDT project/file/design identity comes from `build_ssw_aedt_identity()`, AEDT port ledgers store semantic TX/RX port boundary edge endpoint coordinates from the generated coilmaker tokens, RX normal/spiral semantic edges come from the generated clearance boundary with length equal to realized trace width, ferrite sheet names stay separate from non-model names in the AEDT port ledger, imported object/body names never include the identity hash/stem, and the ANSYS path creates exactly one TX terminal port and one RX terminal port before saving the project.
- Fail-fast points: failed TOML load, failed design-space point identity generation, failed token TOML generation, failed geometry export, missing STEP file, missing token file, missing ledger file, missing TX/RX copper body, missing semantic port token geometry, failed AEDT import, failed lumped-port assignment, failed project save, failed STEP import, or unavailable OCP viewer connection.
- Collaborators: [ssw_step.py](../src/peetsfea/ssw_step.py.md), [ssw_design_space.py](../src/peetsfea/ssw_design_space.py.md), [ssw_ports.py](../src/peetsfea/backend/pyaedt/ssw_ports.py.md).
- Related tests: launched through VS Code task replay plus `tests/test_ssw_step.py` and `tests/test_ssw_design_space.py`.
- Change hazards: preserve `cwd=${workspaceFolder}/run` launch behavior and keep `.vscode/launch.json` pointed at this entrypoint.
- Related plan: [0.3.0 ssw fixed ocp viewer](../../plans/0.3.0-ssw-fixed-ocp-viewer.md).
- Identity plan: [0.3.0 ssw aedt design space identity](../../plans/0.3.0-ssw-aedt-design-space-identity.md).
