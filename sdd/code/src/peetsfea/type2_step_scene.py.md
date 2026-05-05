---
title: type2_step_scene.py
created: 2026-04-28 @ 00:00
updated: 2026-05-04 @ 00:00
tags:
  - step-export
  - type2
  - rxonly
---

# type2_step_scene.py

## Source
- Path: `src/peetsfea/type2_step_scene.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_scene.py.md`
- Status: active

## Responsibility
- Dispatch modeled scene-data construction for active Type2 RxOnly bodies.

## Inputs / Outputs
- Inputs: modeled object spec, placement owner spec, resolved `tx_region.max_z`, deterministic seed.
- Outputs: build123d shapes and `ModeledObjectSceneData` for supported RX modeled objects.

## Canonical State
- RX modeled geometry is represented by returned shapes and scene data.
- TX modeled geometry is not active runtime state.

## Invariants / Fail-Fast
- TX modeled roles fail immediately.
- Supported modeled specs must produce scene data through the role-specific geometry builders.
- `tx_inner_single_coil` and `tx_outer_single_coil` scene building receive `tx_region.max_z` explicitly so passive void-stack sheets can fill to the TX region top without inferring it from inner or outer guide owners.

## Collaborators
- [type2_step_export.py](type2_step_export.py.md)
- [type2_step_ledger.py](type2_step_ledger.py.md)
