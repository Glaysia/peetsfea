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
- `tx_inner_single_coil` underlay repeat count is resolved through the shared scalar resolver. Canonical sampled candidates remain `(0, 2, 4, 6, 8)`, while fixed supported candidates include `1` for the coarsened active TX inner stack.
- `tx_inner_single_coil` underlay PET/PSA/ferrite thickness fields are separately resolved as fixed positive scalars.

## Invariants / fail-fast
- Unknown owner paths fail immediately.
- RxOnly sampled owner discovery must not require TX modeled paths.
- `tx_inner_single_coil` PET/PSA/ferrite underlay thickness resolver contracts reject non-fixed or non-positive values.
- Underlay repeat count resolution rejects non-canonical multi-candidate ranges and fixed values outside the supported fixed candidate set.

## Collaborators
- [type2_step_spec.py](type2_step_spec.py.md)
- [type2_sampled.py](type2_sampled.py.md)
