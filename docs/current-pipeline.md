---
title: current pipeline
created: 2026-04-17 @ 15:55
updated: 2026-04-17 @ 15:55
tags:
  - type2
  - pipeline
---

# Current Pipeline

## Active Path
- The active/default product path is `type2`.
- The canonical public authoring input is `examples/type2_fixed.toml`.
- The active runtime flow is:
  1. `entry/generate_type2_step.py`
  2. `entry/import_type2_step.py`
  3. headless HFSS import/setup-ready validation

## Legacy Path
- `type1` is frozen legacy.
- Legacy type1 code, entrypoints, examples, and tests are opt-in only:
  - `src/peetsfea/legacy/type1/`
  - `entry/legacy/type1/`
  - `tests/legacy/type1/`
  - `examples/legacy/type1.toml`
  - `docs/legacy/type1.md`
  - `docs/legacy/type1.en.md`
- The former type1 current-pipeline writeup now lives at `docs/legacy/current-pipeline-type1.md`.

## Execution Defaults
- Root/default docs, VS Code launch targets, and pytest collection should treat `type2` as the only active path.
- Legacy type1 flows must be invoked explicitly and are not part of the default acceptance surface.
