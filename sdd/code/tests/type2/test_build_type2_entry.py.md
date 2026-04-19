---
title: test_build_type2_entry.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 12:18
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
- default build path keeps setup-ready facade routing for exact plate-stack pair, delegating full-EM-ready setup ownership to that runtime
- explicit runner override is accepted for the exact plate-stack pair without mutating build-entry call wiring
- debug build mode selects exactly one requested design id, forces sequential `jobs=1`, and keeps setup-ready routing
- debug GUI runner constructs a GUI-visible HFSS session with `close_on_exit=False` and delegates release behavior to attached-session setup-ready runtime
- debug CLI rejects missing target design id instead of choosing a manifest entry implicitly
- plate-stack build call shape remains setup-ready oriented (`step_ledger_path`, `output_aedt_path`, `imported_ledger_path`, `design_name`, `design_variables`)
- this suite keeps scope at build-entry wiring and runner handoff contracts, not setup-ready runtime internals
- free plate-stack sampled owners drive non-empty `design_variables` with canonical owner-name order
- active example keeps a shared TX/RX plate-stack PCB total baseline at `0.4 mm`
- active manifest/schema surface no longer carries `shoe_depth_mm`, while sampled `turn_count` / `metal_fill_factor` ranges replay through design variables
- manifest parallelism contracts remain intact

## 변경 시 주의점
- plate-stack setup-ready acceptance와 unsupported role fail-fast를 혼동하지 않는다.
