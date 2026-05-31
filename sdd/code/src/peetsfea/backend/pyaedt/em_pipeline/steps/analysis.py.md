---
title: analysis.py
created: 2026-05-27 @ 00:00
updated: 2026-05-27 @ 00:00
tags:
  - backend
  - em
  - analysis
---

# analysis.py

## Source
- Path: `src/peetsfea/backend/pyaedt/em_pipeline/steps/analysis.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/em_pipeline/steps/analysis.py.md`

## Role
- Owns HFSS setup creation, frequency sweep insertion, and output-variable report creation for the EM pipeline.

## Canonical State
- `Setup1` remains the single driven setup.
- Active type2 report contract inserts a sweep named `Sweep` with `0.1MHz..100MHz` log-scale coverage and the recorded DC subrange.
- `Output Variables Table1` is created against `Setup1 : Sweep` with `Domain := Sweep`.

## Invariants / Fail-Fast
- Existing setup deletion, new setup insertion, sweep insertion, output-variable creation, and report creation are all fail-fast on false returns.
- RX-only mode must reject expressions that still reference `TX_TML`.

## Collaborators
- [type2_step_em_solve.py](../../type2_step_em_solve.py.md)
- [0.2.25-type2-sweep-report-contract](../../../../../../plans/0.2.25-type2-sweep-report-contract.md)
