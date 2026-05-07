---
title: test_build_type2_entry.py
created: 2026-04-18 @ 09:09
updated: 2026-05-07 @ 00:00
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
- Default build batch가 per-design best-effort로 STEP/AEDT skippable failure를 기록하고 나머지 design을 계속 처리하는 계약을 검증한다.
- Default build best-effort는 유효한 STEP ledger, AEDT 파일, imported ledger(일치하는 `source_step_ledger_path` / `aedt_path` / `imported_ledger_path`)가 존재하면 runner 재호출 없이 완성 artifact를 바로 반환한다.
- 부분 출력(누락된 imported ledger 또는 imported ledger 경로 불일치)은 정상 빌드 경로로 runner를 실행한다.
- Related plan: [0.2.24-type2-batch-resume-absolute-sample-index](../../../plans/0.2.24-type2-batch-resume-absolute-sample-index.md).
- TX inner X-position compatibility metadata must stay fixed zero and removed TX outer sampled owners must stay absent.

## Canonical state
- Build path can reuse existing STEP ledger or generate missing RX STEP artifacts.
- Default build returns only successful artifacts while writing/propagating explicit build skip entries for failed design attempts.
- Completed build reuse requires valid STEP ledger plus existing AEDT and imported ledger outputs.
- RX single-coil fixtures use the active `3.965 mm` PCB plus `0.035 mm` copper stack.
- Synthetic TX inner fixtures use active fixed `layer_count=1` plus passive underlay defaults: repeat count `1`, PET/PSA `6.0 mm`, and ferrite `6.0 mm`.
- `tx_region` is allowed only as non-modeled guide context and must include the required `tx_reference_line` ratios; active-shaped synthetic fixtures use the 720.0 mm TX guide X span.
- Synthetic TX guide fixtures mirror the active sweep Z reference range `[false, 0.75, 1.0, 65]`.
- Fake RxOnly specs used by entry tests mirror the current `Type2StepSpec` shape, including `non_model_objects`.
- `config.make_step_on_sample=false` manifest는 build-time STEP generation path를 대표한다.
- Expected sampled owner/design-variable order includes TX inner sampled owners such as `modeled_objects.tx_inner_rect_void_coil.void_stack_present`, but excludes fixed TX inner `x_position_ratio`, before RX coil sampled owners.
- Synthetic source TOML and `ModeledTxInnerSingleCoilSpec` fixtures must expose `void_stack_present` as a sampled integer owner when build design-variable handoff is under test.
- Active single-coil turn-count sweep fixtures cap sampled upper bounds at one below the former maximum: synthetic RX single-coil `turn_count` uses `2.0..5.0` with `count=4`, embedded sampled TOML uses `[true, 2, 5, 4]`, and non-`turn_count` owners remain unchanged; fixed singleton `turn_count` ranges remain unchanged.
- Active fixed/sweep source fixtures use `modeled_objects.tx_inner_rect_void_coil.layer_count = [true, 1, 1, 1]`, and build design variables exclude layer count.
- Fixed singleton TX guide X ratio must not become a build design variable, while sampled TX guide Y ratio remains exported when `count > 1`.
- Build design variables must not include `modeled_objects_tx_outer_rect_void_coil_*`.

## Invariants / fail-fast
- Unsupported role sets fail before backend execution.
- RxOnly build tests must not require EM-active TX modeled objects.
- Geometry-only `tx_inner_single_coil` can accompany RX without activating removed TX outer modeled roles.
- Passive `tv_aluminum_plate` can accompany the active RX/TX-inner role set without being treated as an EM target.
- TX modeled build dependencies, including TX columns paired with RX, must not reach the setup-ready runner.
- Prepared build validation must reject missing or nonzero TX inner X-position compatibility ranges before setup-ready execution.
- Best-effort build tests catch only declared skippable runtime exceptions; unsupported role validation remains fail-fast before skip recording.

### Build resume contract covered here
- `_is_resume_ready_type2_build()`의 조건을 실무 계약으로 검증: 
  - `step_ledger_path`에 유효한 STEP ledger가 존재
  - `aedt_path` 파일이 존재
  - `imported_ledger_path` 파일이 존재
  - imported ledger JSON의 `source_step_ledger_path`, `aedt_path`, `imported_ledger_path`가 각각 현 design의 경로와 정규화 후 일치
- 위 조건 중 하나라도 실패하면 best-effort가 runner를 실행해 완료 artifact를 새로 생성한다.

## Collaborators
- [build.py](../../entry/build.py.md)
- [type2_runtime.py](../../src/peetsfea/type2_runtime.py.md)
- [type2_step_spec.py](../../src/peetsfea/type2_step_spec.py.md)
- [0.2.24 Type2 TX Outer Void Stack](../../../plans/0.2.24-type2-tx-outer-void-stack.md)
- [0.2.24-view-step-gui-setup-ready](../../../plans/0.2.24-view-step-gui-setup-ready.md)
- [0.2.24-type2-tx-region-y-1800-x-reference-fixed](../../../plans/0.2.24-type2-tx-region-y-1800-x-reference-fixed.md)
- [0.2.24-type2-turn-count-sweep-upper-bound](../../../plans/0.2.24-type2-turn-count-sweep-upper-bound.md)
