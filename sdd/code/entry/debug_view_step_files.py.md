---
title: debug_view_step_files.py
created: 2026-06-01
updated: 2026-06-01
tags:
  - sdd
  - code
  - debug
---

# debug_view_step_files.py

- Path: `entry/debug_view_step_files.py`
- Responsibility: provide the single VS Code F5 debug entrypoint that generates the minimal STEP artifact and sends it to OCP CAD Viewer.
- Inputs: `examples/minimal_step_two_port.toml` through `entry/sample.py`.
- Outputs: generated STEP artifacts, an OCP CAD Viewer `show(...)` call, and a printed JSON summary containing the selected design ID, STEP path, ledger path, body names, copper body names, and port sheet names.
- Canonical state: `run/sampled/minimal/manifest.json` and the generated entry's `minimal_step_ledger.json`.
- Invariants: `VIEW_INDEX = -1` selects the latest manifest entry; non-negative indices address the manifest entries directly.
- Fail-fast points: failed sample generation, empty manifest entries, out-of-range view index, missing STEP file, missing ledger file, invalid ledger JSON, failed STEP import, or unavailable OCP viewer connection.
- Collaborators:
  - [sample.py](sample.py.md)
  - [minimal_step.py](../src/peetsfea/minimal_step.py.md)
- Related tests: launched through VS Code task replay and sample smoke validation.
- Change hazards: keep `.vscode/launch.json` pointed at this single F5 entrypoint; do not reintroduce Type2 manifest compatibility, GUI AEDT launch behavior, notebook-style cleanup, or build/solve launch configurations.
- Related plan: [0.3.0 minimal step two port reset](../../plans/0.3.0-minimal-step-two-port-reset.md).
