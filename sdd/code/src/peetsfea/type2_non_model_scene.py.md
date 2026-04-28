---
title: type2_non_model_scene.py
created: 2026-04-28 @ 00:00
updated: 2026-04-28 @ 00:00
tags:
  - step-export
  - type2
  - rxonly
---

# type2_non_model_scene.py

## Source
- Path: `src/peetsfea/type2_non_model_scene.py`
- Code note path: `sdd/code/src/peetsfea/type2_non_model_scene.py.md`
- Status: active

## Responsibility
- Resolve and build non-modeled Type2 guide/context scene members.

## Inputs / Outputs
- Inputs: non-modeled base and derived specs, deterministic seed.
- Outputs: non-modeled scene shapes and ledger entries.

## Canonical State
- `environment`, `tx_region`, and `rx_region_max` are the active visible non-modeled scene members.
- `tx_region_actual` and `tx_region_actual_stack_space` derived specs are inactive for RxOnly scene export.

## Invariants / Fail-Fast
- Visible groups must resolve from required specs.
- Grouped visible geometry must form exactly one solid.
- Derived TX actual placement helpers remain fail-fast if called by unsupported paths.

## Collaborators
- [type2_step_export.py](type2_step_export.py.md)
- [type2_step_ledger.py](type2_step_ledger.py.md)
