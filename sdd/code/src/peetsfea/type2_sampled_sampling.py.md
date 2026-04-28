---
title: type2_sampled_sampling.py
created: 2026-04-20 @ 00:00
updated: 2026-04-28 @ 00:00
tags:
  - sampling
---

# type2_sampled_sampling.py

## Source
- Path: `src/peetsfea/type2_sampled_sampling.py`
- Code note path: `sdd/code/src/peetsfea/type2_sampled_sampling.py.md`
- Status: active

## 역할
- sampled owner candidate selection, retry, and freeze logic을 구현한다.
- 0.2.24 SDD 기준 RX sampled owners and shared constraints are active.

## 입력 / 출력
- 입력: source spec, seed, sample index, retry number
- 출력: frozen sampled values and sampled metadata

## Canonical state
- Same source spec + version + seed + retry number yields deterministic sampled values.
- RxOnly sampling does not require TX modeled owner values.

## Invariants / fail-fast
- Unknown owner paths fail immediately.
- Constraint exhaustion is recorded only through the explicit skipped-attempt path.
- Non-validation exceptions remain fail-fast.

## Collaborators
- [type2_sampled.py](type2_sampled.py.md)
- [type2_step_spec_sampling.py](type2_step_spec_sampling.py.md)
