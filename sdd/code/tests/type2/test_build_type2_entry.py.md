---
title: test_build_type2_entry.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 13:08
tags:
  - tests
  - type2
  - build
---

# test_build_type2_entry.py

## Source
- Path: `tests/type2/test_build_type2_entry.py`
- Code note path: `sdd/code/tests/type2/test_build_type2_entry.py.md`
- Direct owner: [[sdd/plans/0.2.22-type2-sampled-build-split]], [[sdd/plans/0.2.22-type2-plate-stack-z-usage-ratio]], [[sdd/plans/0.2.22-type2-plate-stack-y-usage-ratio]], [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]], [[sdd/plans/0.2.22-type2-single-coil-void-usage-ratio]], [[sdd/plans/0.2.22-type2-tx-actual-region-non-model-sampling]]
- Direct verification target: [[sdd/code/entry/build.py]]
- Discovery bridge: [[sdd/code/tests/type2/test_sample_type2_entry.py]]

## 역할
- build entry/runtime wiring과 manifest-driven runner behavior를 검증한다.

## Canonical coverage
- active RX single-coil manifest uses build-entry/runner handoff without TX assumptions.
- default build path keeps setup-ready facade routing for `rx_single_coil` entries, delegating full-EM-ready setup ownership to that runtime.
- explicit runner override is accepted for the active RX-only path without mutating build-entry call wiring.
- type2 runtime build preflight accepts active RX-only prepared builds and rejects unsupported role sets before runner execution.
- debug build mode selects exactly one requested design id, forces sequential `jobs=1`, and keeps setup-ready routing
- debug GUI runner constructs a GUI-visible HFSS session with `close_on_exit=False` and delegates release behavior to attached-session setup-ready runtime
- debug CLI rejects missing target design id instead of choosing a manifest entry implicitly
- build call shape remains setup-ready oriented (`step_ledger_path`, `output_aedt_path`, `imported_ledger_path`, `design_name`, `design_variables`)
- this suite keeps scope at build-entry wiring and runner handoff contracts, not setup-ready runtime internals
- sampled owner replay drives non-empty RX `design_variables` with canonical owner-name order
- sampled owner replay now also drives unitless `tx_region_actual` non-model usage-ratio design variables.
- RX effective sampled owners are `outer_x_usage_ratio`, `outer_y_usage_ratio`, `void_usage_ratio`, `turn_count`, `metal_fill_factor`; `layer_count`, full-backing `underlay_repeat_count`, and removed split/centered `void_*` fields are excluded from `design_variables`
- manifest parallelism contracts remain intact

## 변경 시 주의점
- RX build path checks are independent of TX policy and still reject unsupported roles.
- TX actual-region non-model owners must not change modeled role preflight; active modeled role remains `rx_single_coil`.
