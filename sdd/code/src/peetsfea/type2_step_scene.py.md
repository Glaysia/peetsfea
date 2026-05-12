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
- Add modeled TV aluminum sheet ledger construction when role is `tv_aluminum_plate`.

## Inputs / Outputs
- Inputs: modeled object spec, placement owner spec, resolved `tx_region.max_z`, deterministic seed.
- Outputs: build123d shapes and `ModeledObjectSceneData` for supported RX objects, plus zero-body `ModeledObjectSceneData` for the modeled TV aluminum sheet.

## Canonical State
- RX modeled geometry is represented by returned shapes and scene data.
- TX modeled geometry is not active runtime state.
- TV aluminum plate geometry is represented as a zero-thickness sheet on the source `tv` `+X` face; it is canonical ledger state and not a STEP solid.
- TV aluminum sheet canonical metadata records `source_non_model_object_id = "tv"`, `source_face = "+X"`, resolved `sheet_present`, `sheet_thickness_mm`, and the four sheet vertices.

## Invariants / Fail-Fast
- TX modeled roles fail immediately.
- Supported modeled specs must produce scene data through role-specific builders.
- `tv_aluminum_plate` requires owner `tv`, and fails immediately if the owner is missing expected identity or has non-finite/non-positive geometry bounds.
- TV aluminum sheet thickness must remain finite and positive, but that thickness is metadata for downstream finite-conductivity setup rather than exported body depth.
- `sheet_present` is resolved deterministically from the modeled object's integer range and seed; only canonical boolean candidates are accepted.
- `tx_inner_single_coil` and `tx_outer_single_coil` scene building receive `tx_region.max_z` explicitly so passive void-stack sheets can fill to the TX region top without inferring it from inner or outer guide owners.

## Collaborators
- [type2_step_export.py](type2_step_export.py.md)
- [type2_step_ledger.py](type2_step_ledger.py.md)
