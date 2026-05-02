---
title: type2_single_coil_scene.py
created: 2026-04-20 @ 00:00
updated: 2026-04-30 @ 23:59
tags:
  - rx
  - scene
---

# type2_single_coil_scene.py

## Source
- Path: `src/peetsfea/type2_single_coil_scene.py`
- Code note path: `sdd/code/src/peetsfea/type2_single_coil_scene.py.md`
- Status: active

## 역할
- RX single-coil and geometry-only TX inner/outer single-coil scene assembly helper다.
- Expose shared owner-scaled sizing/placement helper data needed by non-model actual-region resolution, including the resolved design outer box separately from physical modeled body bounds.

## Invariants / fail-fast
- Invalid RX scene dimensions fail immediately.
- Invalid TX inner scene dimensions fail immediately.
- TX inner scene assembly computes mm outer ranges from the resolved `tx_inner_region` owner before building the rect-void geometry.
- TX inner scene placement centers the realized coil footprint inside `tx_inner_region`; only legacy/direct `tx_region` TX placement touches the owner's min-X face.
- TX outer scene assembly computes mm outer ranges from the resolved `tx_outer_region` owner and uses the same inner-owned sampled geometry/topology values, with separate `tx_outer_single_coil` profile identity and terminal metadata.
- TX outer scene assembly uses a rigid tilted frame derived from `tx_outer_region_prism`: local +X follows the semantic inner-to-outer top edge, local +Y follows world +Y, and local +Z is the rotated stack normal.
- TX outer scene placement must read `tx_outer_region` creation-time prism provenance from the non-model scene; it must not sort or reverse-calculate the sloped prism from downstream modeled bodies.
- TX outer owner-scaled `outer_x_mm` uses the sloped top-face length. The slight world +X protrusion created by stacking along the tilted local normal is accepted for this role.
- Actual-region helpers must expose the resolved design outer box (`outer_x_mm`/`outer_y_mm`) and must not substitute the smaller decomposed material/body bbox for canonical actual-region bounds.
- `RealizedSingleCoilFitEnvelope.design_outer_bounds_*` and `outer_bounds_*` are the resolved design outer box intended for actual-region bounds.
- `RealizedSingleCoilFitEnvelope.physical_modeled_body_bounds_*` describes the exported physical modeled body bbox used by modeled scene assembly.
- TX ferrite/underlay contracts are not active for `tx_inner_single_coil`.
- TX ferrite/underlay contracts are not active for `tx_outer_single_coil`.

## Collaborators
- [type2_step_scene.py](type2_step_scene.py.md)
- [0.2.24 Type2 TX Actual Regions](../../../plans/0.2.24-type2-tx-actual-regions.md)
- [0.2.24 Type2 TX Outer Single Coil](../../../plans/0.2.24-type2-tx-outer-single-coil.md)
