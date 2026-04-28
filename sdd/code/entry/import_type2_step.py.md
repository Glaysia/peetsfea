---
title: import_type2_step.py
created: 2026-04-17 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - entry
  - import
---

# import_type2_step.py

## Source
- Path: `entry/import_type2_step.py`
- Code note path: `sdd/code/entry/import_type2_step.py.md`
- Status: active

## 역할
- type2 STEP import-only entrypoint다.
- 0.2.24 SDD 기준 RX import and non-modeled guide/context import are active.

## Invariants / fail-fast
- Import failures raise immediately.
- Import-only creates no mesh, boundary, ports, or reports.

## Collaborators
- [type2_step_import_pipeline.py](../src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py.md)
