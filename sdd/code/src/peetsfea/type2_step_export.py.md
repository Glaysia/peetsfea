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
- Build the active Type2 STEP scene and ledger artifacts for RxOnly export.
- Reject modeled TX export requests with actionable errors.

## Inputs / Outputs
- Inputs: Type2 TOML path, output directory, ledger path, deterministic seed, optional stage reporter.
- Outputs: combined STEP scene, per-modeled-object metadata for RX bodies, `Type2StepLedger`.

## Canonical State
- RX modeled body names, body groups, canonical coordinates, and terminal metadata are export-owned.
- `tx_region` remains non-modeled guide context only.
- TX modeled object specifications are unsupported in active RxOnly export.

## Invariants / Fail-Fast
- Modeled TX roles fail before scene construction.
- STEP export must return `True`.
- Scene body labels must be unique.
- RX terminal metadata must match the geometry contract.

## Collaborators
- [type2_step_ledger.py](type2_step_ledger.py.md)
- [type2_non_model_scene.py](type2_non_model_scene.py.md)
- [type2-em-report-contract](../../../architecture/type2-em-report-contract.md)
