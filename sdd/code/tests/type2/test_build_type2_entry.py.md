---
title: test_build_type2_entry.py
created: 2026-04-18 @ 09:09
updated: 2026-05-06 @ 00:00
tags:
  - test
  - build
---

# test_build_type2_entry.py

## Source
- Path: `tests/type2/test_build_type2_entry.py`
- Code note path: `sdd/code/tests/type2/test_build_type2_entry.py.md`
- Status: active

## 역할
- type2 build entrypoint and sampled/build handoff behavior를 검증한다.
- 0.2.24 SDD 기준 RxOnly build path is the active documented target.
- solve-enabled build handoff and the geometry-only `tx_inner_single_coil` plus RX role gate are covered.
- Sample-only manifest에서 build가 missing STEP ledger를 생성하고, existing ledger는 exporter 없이 재사용하는 계약을 검증한다.
- TX inner X-position sampled owner metadata must become a build design variable while removed TX outer sampled owners stay absent.

## Canonical state
- Build path can reuse existing STEP ledger or generate missing RX STEP artifacts.
- RX single-coil fixtures use the active `3.965 mm` PCB plus `0.035 mm` copper stack.
- `tx_region` is allowed only as non-modeled guide context and must include the required `tx_reference_line` ratios.
- Fake RxOnly specs used by entry tests mirror the current `Type2StepSpec` shape, including `non_model_objects`.
- `config.make_step_on_sample=false` manifest는 build-time STEP generation path를 대표한다.
- Expected sampled owner/design-variable order includes `modeled_objects.tx_inner_rect_void_coil.x_position_ratio` before RX coil sampled owners.
- Fixed singleton TX guide X ratio must not become a build design variable, while sampled TX guide Y ratio remains exported when `count > 1`.
- Build design variables must not include `modeled_objects_tx_outer_rect_void_coil_*`.

## Invariants / fail-fast
- Unsupported role sets fail before backend execution.
- RxOnly build tests must not require EM-active TX modeled objects.
- Geometry-only `tx_inner_single_coil` can accompany RX without activating removed TX outer modeled roles.
- TX modeled build dependencies, including TX columns paired with RX, must not reach the setup-ready runner.
- Prepared build validation must reject missing or unfrozen TX inner X-position source ranges before setup-ready execution.

## Collaborators
- [build.py](../../entry/build.py.md)
- [type2_runtime.py](../../src/peetsfea/type2_runtime.py.md)
- [type2_step_spec.py](../../src/peetsfea/type2_step_spec.py.md)
- [0.2.24 Type2 TX Outer Void Stack](../../../plans/0.2.24-type2-tx-outer-void-stack.md)
- [0.2.24-view-step-gui-setup-ready](../../../plans/0.2.24-view-step-gui-setup-ready.md)
- [0.2.24-type2-tx-region-y-1800-x-reference-fixed](../../../plans/0.2.24-type2-tx-region-y-1800-x-reference-fixed.md)
