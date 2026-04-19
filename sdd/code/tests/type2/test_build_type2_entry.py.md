---
title: test_build_type2_entry.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 00:42
tags:
  - tests
  - type2
  - build
---

# test_build_type2_entry.py

## Source
- Path: `tests/type2/test_build_type2_entry.py`
- Code note path: `sdd/code/tests/type2/test_build_type2_entry.py.md`
- Direct owner: [[sdd/plans/0.2.22-type2-sampled-build-split]]
- Direct verification target: [[sdd/code/entry/build.py]]
- Discovery bridge: [[sdd/code/tests/type2/test_sample_type2_entry.py]]

## 역할
- build entry/runtime wiring과 manifest-driven runner behavior를 검증한다.

## Canonical coverage
- active plate-stack manifest can still export missing STEP
- default build path keeps setup-ready facade routing for exact plate-stack pair
- explicit setup-ready runner override is accepted for exact plate-stack pair
- plate-stack build call shape remains port-ready oriented (`step_ledger_path`, `output_aedt_path`, `imported_ledger_path`, `design_name`, `design_variables`)
- fixed plate-stack sampled ranges keep design-variable passing empty in current baseline
- active example keeps a shared TX/RX plate-stack PCB total baseline at `0.4 mm`
- active manifest/schema surface no longer carries `shoe_depth_mm`, while fixed `turn_count` / `metal_fill_factor` ranges still replay losslessly
- manifest parallelism contracts remain intact

## 변경 시 주의점
- plate-stack setup-ready acceptance와 unsupported role fail-fast를 혼동하지 않는다.
