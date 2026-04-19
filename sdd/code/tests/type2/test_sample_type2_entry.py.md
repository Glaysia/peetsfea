---
title: test_sample_type2_entry.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 23:58
tags:
  - tests
  - type2
  - sampling
---

# test_sample_type2_entry.py

## Source
- Path: `tests/type2/test_sample_type2_entry.py`
- Code note path: `sdd/code/tests/type2/test_sample_type2_entry.py.md`
- Direct owner: [[sdd/plans/0.2.22-type2-sampled-build-split]]
- Direct verification target: [[sdd/code/entry/sample.py]]
- Discovery bridge: [[sdd/code/tests/type2/test_build_type2_entry.py]]

## 역할
- sampled TOML, manifest metadata, sampled owner-path selection contract를 검증한다.

## Canonical coverage
- active example uses `tx_plate_stack` + `rx_plate_stack`
- active example plate-stack PCB total uses a shared TX/RX baseline of `0.4 mm`
- plate roles can own sampled ranges, but current fixed example does not contribute sampled owner paths
- sampled TOML keeps plate scalar fields fixed
- sampled TOML keeps fixed `turn_count`, `metal_fill_factor` range tables losslessly
- sampled TOML excludes removed `shoe_depth_mm` from both modeled payload and sampled metadata
- manifest identity and hash contract remain unchanged

## 변경 시 주의점
- sampled owner assertions를 role-blind coil field enumeration으로 되돌리지 않는다.
