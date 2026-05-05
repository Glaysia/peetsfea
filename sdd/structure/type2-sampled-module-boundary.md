---
title: Type2 Sampled Module Boundary
created: 2026-04-18 @ 09:09
updated: 2026-05-03 @ 00:00
tags:
  - structure
  - sampling
---

# Type2 Sampled Module Boundary

## Boundary
- `type2_step_spec*` owns parsing and owner discovery.
- `type2_sampled*` owns deterministic candidate selection, constraints, retry, and sampled TOML rendering.
- `type2_runtime` owns build orchestration.

## Graph Position
- Public sampled orchestration: [type2_sampled.py](../code/src/peetsfea/type2_sampled.py.md)
- Candidate selection and retry logic: [type2_sampled_sampling.py](../code/src/peetsfea/type2_sampled_sampling.py.md)
- Skipped-attempt ledger shape: [type2_sampled_skip.py](../code/src/peetsfea/type2_sampled_skip.py.md)
- Spec owner discovery boundary: [type2-spec-boundary](../architecture/type2-spec-boundary.md)

## 0.2.24 Reset
- Active sampled SDD contract is RX/RxOnly plus shared execution metadata.
- `tx_region` remains guide context only.
- TX shape-specific sampled owners are removed from SDD until a future TX plan reintroduces them.
