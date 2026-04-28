---
title: test_sample_type2_entry.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - test
  - sampling
---

# test_sample_type2_entry.py

## Source
- Path: `tests/type2/test_sample_type2_entry.py`
- Code note path: `sdd/code/tests/type2/test_sample_type2_entry.py.md`
- Status: active

## 역할
- type2 sampling entrypoint and manifest behavior를 검증한다.
- 0.2.24 SDD 기준 RxOnly owner discovery and guide/context handling are active.

## Canonical state
- Sampling remains deterministic by source TOML, version, seed, and retry number.
- `tx_region` is fixed guide context only.
- RxOnly sampled-owner fixtures contain only RX coil owners; TX derived non-model owners are absent.

## Invariants / fail-fast
- Unknown owner paths fail immediately.
- RxOnly sampling tests must not require TX modeled owners.
- RxOnly sampling tests must not require `tx_region_actual` or `tx_region_actual_stack_space`.
- TX modeled-role fixtures assert parser/sampling fail-fast behavior instead of sampled manifest success.

## Collaborators
- [sample.py](../../entry/sample.py.md)
- [type2_sampled.py](../../src/peetsfea/type2_sampled.py.md)
