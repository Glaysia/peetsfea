---
title: type2_step_import_pipeline.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - import
  - pyaedt
---

# type2_step_import_pipeline.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py.md`
- Status: active

## 역할
- Import-only CLI/runtime facade다.
- 0.2.24 SDD 기준 RX import and non-modeled guide/context import are active.

## Canonical state
- Import-only does not create mesh, boundary, ports, or reports.
- `tx_region` guide context is allowed; TX modeled geometry is not required.

## Invariants / fail-fast
- Import failures and PyAEDT false returns fail immediately.

## Collaborators
- [type2_step_import_core.py](type2_step_import_core.py.md)
