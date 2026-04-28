---
title: Type2 Sampled Module Boundary
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - structure
  - sampling
---

# Type2 Sampled Module Boundary

## Boundary
- `type2_step_spec*` owns parsing and owner discovery.
- `type2_sampled*` owns deterministic candidate selection, constraints, retry, and sampled TOML rendering.
- `type2_runtime` owns build orchestration.

## 0.2.24 Reset
- Active sampled SDD contract is RX/RxOnly plus shared execution metadata.
- `tx_region` remains guide context only.
- TX shape-specific sampled owners are removed from SDD until a future TX plan reintroduces them.
