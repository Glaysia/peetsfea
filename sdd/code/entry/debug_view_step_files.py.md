---
title: debug_view_step_files.py
created: 2026-05-27 @ 00:00
updated: 2026-05-27 @ 00:00
tags:
  - entry
  - step-viewer
  - debug
---

# debug_view_step_files.py

## Source
- Path: `entry/debug_view_step_files.py`
- Code note path: `sdd/code/entry/debug_view_step_files.py.md`
- Related export owner: [type2_step_export.py](../src/peetsfea/type2_step_export.py.md)

## Role
- Provides the editable Python Type2 STEP viewer/debug entry alongside the existing notebook surface.
- Regenerates the fixed example STEP when `VIEW_INDEX == -1`.
- Opens sampled manifest STEP artifacts when `VIEW_INDEX >= 0`, refreshing STEP/ledger files from sampled TOML before display or GUI setup.
- Shows the selected scene through `ocp_vscode`.
- Runs the AEDT setup path by default through `BUILD_W_GUI = True`; callers that need STEP/viewer-only validation must pass `--no-build-w-gui`.

## Inputs / Outputs
- Inputs:
  - `examples/type2_fixed.toml`
  - `run/sampled/type2/manifest.json`
  - command-line overrides `--view-index` and `--build-w-gui` / `--no-build-w-gui`
- Outputs:
  - refreshed fixed/sampled `type2_scene.step`
  - refreshed fixed/sampled `type2_step_ledger.json`
  - OCP VS Code viewer objects
  - optional GUI AEDT debug artifacts

## Canonical State
- `VIEW_INDEX == -1` means fixed example view.
- `VIEW_INDEX >= 0` means lookup by concrete manifest `sample_index`.
- `BUILD_W_GUI = True` is the default so direct debug runs exercise the AEDT setup path.
- The STEP ledger path is canonical for downstream GUI setup.
- A process-local sampled refresh registry prevents duplicate export when the same sample is displayed and then sent into GUI setup in the same process.

## Invariants / Fail-Fast
- Manifest selection must resolve exactly one entry by `sample_index`.
- Manifest path/string/integer fields must have concrete runtime types.
- Sampled STEP and ledger files are regenerated from sampled TOML and manifest seed even when files already exist.
- A regenerated sampled STEP path must match manifest `scene_step_path`.
- Unknown or duplicate manifest selection raises immediately.

## Collaborators
- [type2_step_export.py](../src/peetsfea/type2_step_export.py.md)
- [sample.py](sample.py.md)
- [build.py](build.py.md)
- [type2_step_setup_ready.py](../src/peetsfea/backend/pyaedt/type2_step_setup_ready.py.md)

## Change Hazards
- Keep the top constants easy to edit for direct debugger use.
- Do not add notebook-only cleanup hooks or fallback path selection.
