---
title: test_generate_type2_step.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 23:55
tags:
  - test
  - step-export
---

# test_generate_type2_step.py

## Source
- Path: `tests/type2/test_generate_type2_step.py`
- Code note path: `sdd/code/tests/type2/test_generate_type2_step.py.md`
- Status: active

## 역할
- type2 STEP export and ledger contract를 검증한다.
- 0.2.24 SDD 기준 RX geometry plus retained non-modeled guide/context are active.

## Canonical state
- RX exported body names/counts and terminal metadata remain deterministic.
- `tx_region` may be present as guide context only.
- `tx_reference_line` ratio inputs, including centered `y_usage_ratio`, are expected to derive a visible non-modeled
  `tx_inner_region` STEP and retained ledger member without activating TX
  modeled geometry.

## Invariants / fail-fast
- Exported body drift and generic names fail.
- RxOnly export tests must not require TX modeled geometry.
- TX reference-line X/Z ratios must be strictly inside `(0, 1)`, Y usage ratio must be in `(0, 1]`, and invalid ratios
  must fail before STEP construction.

## Collaborators
- [generate_type2_step.py](../../entry/generate_type2_step.py.md)
- [type2_step_export.py](../../src/peetsfea/type2_step_export.py.md)
- [0.2.24-type2-tx-inner-region-non-model-step](../../../plans/0.2.24-type2-tx-inner-region-non-model-step.md)
