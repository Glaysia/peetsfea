---
title: type2_step_spec_sampling.py
created: 2026-04-20 @ 00:00
updated: 2026-04-28 @ 00:00
tags:
  - spec
  - sampling
---

# type2_step_spec_sampling.py

## Source
- Path: `src/peetsfea/type2_step_spec_sampling.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_spec_sampling.py.md`
- Status: active

## 역할
- type2 source spec에서 sampled owner paths를 도출한다.
- 0.2.24 SDD 기준 RX owner paths and shared constraints are active.

## 입력 / 출력
- 입력: parsed type2 spec
- 출력: ordered sampled owner descriptors

## Canonical state
- Owner paths remain deterministic and source-order stable.
- `tx_region` is fixed guide context, not sampled TX geometry.

## Invariants / fail-fast
- Unknown owner paths fail immediately.
- RxOnly sampled owner discovery must not require TX modeled paths.

## Collaborators
- [type2_step_spec.py](type2_step_spec.py.md)
- [type2_sampled.py](type2_sampled.py.md)
