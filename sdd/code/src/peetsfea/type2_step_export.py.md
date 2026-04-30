---
title: type2_step_export.py
created: 2026-04-28 @ 00:00
updated: 2026-04-30 @ 00:00
tags:
  - step-export
  - type2
  - rxonly
---

# type2_step_export.py

## Source
- Path: `src/peetsfea/type2_step_export.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_export.py.md`
- Status: active

## Responsibility
- Build the active Type2 STEP scene and ledger artifacts for RxOnly EM export.
- Allow geometry-only `tx_inner_single_coil` and derived `tx_outer_single_coil` STEP bodies while keeping new TX parallel wiring out of scope for this step.
- Pass modeled specs into non-model guide resolution so `tx_outer_region` can derive stack height from active TX inner stack parameters.
- Pass enough modeled sizing context into non-model scene resolution for `tx_inner_actual_region` to be resolved before modeled coil STEP construction.
- Reject legacy/generic modeled TX export requests with actionable errors.

## Inputs / Outputs
- Inputs: Type2 TOML path, output directory, ledger path, deterministic seed, optional stage reporter.
- Outputs: combined STEP scene, per-modeled-object metadata for RX bodies and geometry-only TX inner/outer bodies, `Type2StepLedger`.

## Canonical State
- RX modeled body names, body groups, canonical coordinates, and terminal metadata are export-owned.
- `tx_region`/`tx_inner_region` remain non-modeled guide context and placement owner context.
- `tx_outer_region` remains non-modeled guide context and follows `tx_region`/`tx_inner_region` semantic edges.
- `tx_inner_actual_region` remains non-modeled context and mirrors the TX inner coil-fit envelope without becoming the modeled coil placement owner.
- `tx_inner_single_coil` may be exported as modeled geometry, but not consumed for active TX ports, sources, or reports.
- `tx_inner_single_coil` geometry and terminal metadata validation use centered X/Y placement inside `tx_inner_region`.
- `tx_outer_single_coil` may be exported as modeled geometry by deriving numeric ranges from the inner TX modeled spec and placing the body in `tx_outer_region`.
- `tx_outer_single_coil` terminal metadata is independently fixed to `A_cw_to_a`; sampling ownership remains under `tx_inner_rect_void_coil`.
- Generic `tx_single_coil`, `tx_plate_stack`, and `tx_rect_void_columns` remain unsupported in active RxOnly export.

## Invariants / Fail-Fast
- Generic modeled TX roles fail before scene construction.
- `tx_inner_single_coil` placement uses the resolved `tx_inner_region`; later code must not reverse-calculate that region from imported geometry.
- `tx_outer_region` height uses resolved modeled `tx_inner_single_coil` layer parameters and must not use literal example coordinates.
- `tx_inner_actual_region` sizing must match modeled `tx_inner_single_coil` sizing for the same seed and must not create active EM setup changes.
- `tx_outer_actual_region`, once emitted, must match modeled `tx_outer_single_coil` sizing for the same seed and must not be populated from guide-only data.
- STEP export must return `True`.
- Scene body labels must be unique.
- RX terminal metadata must match the geometry contract.

## Collaborators
- [type2_step_ledger.py](type2_step_ledger.py.md)
- [type2_non_model_scene.py](type2_non_model_scene.py.md)
- [type2-em-report-contract](../../../architecture/type2-em-report-contract.md)
- [0.2.24 Type2 TX Outer Single Coil](../../../plans/0.2.24-type2-tx-outer-single-coil.md)
