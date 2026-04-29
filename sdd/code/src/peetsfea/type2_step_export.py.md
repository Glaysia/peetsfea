---
title: type2_step_export.py
created: 2026-04-28 @ 00:00
updated: 2026-04-28 @ 00:00
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
- Allow geometry-only `tx_inner_single_coil` STEP bodies while keeping TX EM setup inactive.
- Reject legacy/generic modeled TX export requests with actionable errors.

## Inputs / Outputs
- Inputs: Type2 TOML path, output directory, ledger path, deterministic seed, optional stage reporter.
- Outputs: combined STEP scene, per-modeled-object metadata for RX bodies and geometry-only TX inner bodies, `Type2StepLedger`.

## Canonical State
- RX modeled body names, body groups, canonical coordinates, and terminal metadata are export-owned.
- `tx_region`/`tx_inner_region` remain non-modeled guide context and placement owner context.
- `tx_inner_single_coil` may be exported as modeled geometry, but not consumed for active TX ports, sources, or reports.
- `tx_inner_single_coil` geometry and terminal metadata validation use centered X/Y placement inside `tx_inner_region`.
- Generic `tx_single_coil`, `tx_plate_stack`, and `tx_rect_void_columns` remain unsupported in active RxOnly export.

## Invariants / Fail-Fast
- Generic modeled TX roles fail before scene construction.
- `tx_inner_single_coil` placement uses the resolved `tx_inner_region`; later code must not reverse-calculate that region from imported geometry.
- STEP export must return `True`.
- Scene body labels must be unique.
- RX terminal metadata must match the geometry contract.

## Collaborators
- [type2_step_ledger.py](type2_step_ledger.py.md)
- [type2_non_model_scene.py](type2_non_model_scene.py.md)
- [type2-em-report-contract](../../../architecture/type2-em-report-contract.md)
