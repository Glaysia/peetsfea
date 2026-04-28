---
title: type2_step_spec_non_model.py
created: 2026-04-20 @ 00:00
updated: 2026-04-28 @ 00:00
tags:
  - spec
  - non-model
---

# type2_step_spec_non_model.py

## Source
- Path: `src/peetsfea/type2_step_spec_non_model.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_spec_non_model.py.md`
- Status: active

## 역할
- type2 non-model object parsing and validation helper다.

## Canonical state
- `tx_region` remains as future placement guide context.
- RX region/context objects remain available to RX export/setup paths.
- Derived TX actual/stack-space shape contracts are not active SDD contracts during the reset.

## Invariants / fail-fast
- Missing required non-model context or unsupported object ids fail immediately.
- Non-model guide objects must not create TX modeled geometry, ports, or output variables in RxOnly.

## Collaborators
- [type2_step_spec.py](type2_step_spec.py.md)
