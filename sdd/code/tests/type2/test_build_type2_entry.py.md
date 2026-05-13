---
title: test_build_type2_entry.py
created: 2026-04-18 @ 09:09
updated: 2026-05-13 @ 00:00
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
- Default build best-effort는 target AEDT 파일명 또는 exact `.aedt.done` marker가 이미 존재하면 imported ledger의 존재 여부나 경로 일치 여부와 무관하게 STEP exporter/AEDT runner 재호출 없이 완성 artifact를 바로 반환한다.
- Target AEDT 파일과 exact marker가 모두 누락된 부분 출력은 정상 빌드 경로로 runner를 실행한다.
- Default build entry tests cover that recorded skips are surfaced as entry failures after the skip ledger is written.
- Related plan: [0.2.24-type2-batch-resume-absolute-sample-index](../../../plans/0.2.24-type2-batch-resume-absolute-sample-index.md).
- TX inner X-position compatibility metadata must stay fixed zero and removed TX outer sampled owners must stay absent.
- Default Type2 build retries only `Type2AedtWorkerProcessError` from the persistent AEDT worker path, waits 60 seconds between restarts, and stops after the configured production restart limit.
- Persistent AEDT worker launch coverage asserts the default 1-second start-event stagger and verifies the starter does not wait for each worker's ready message before starting the next worker.

## Canonical state
- Build path can reuse existing STEP ledger or generate missing RX STEP artifacts.
- Default build returns only successful artifacts while writing/propagating explicit build skip entries for failed design attempts.
- Build CLI must not treat `built=0 skipped>0` as success.
- Completed build reuse requires only existing target AEDT readiness: the target `.aedt` path or exact `<target>.aedt.done` marker. STEP and imported ledger paths are returned from the prepared build contract without requiring their files to exist.
- RX single-coil fixtures use the active `3.965 mm` PCB plus `0.035 mm` copper stack.
- Synthetic TX inner fixtures use active fixed `layer_count=1` plus passive underlay defaults: repeat count `1`, PET/PSA `6.0 mm`, and ferrite `6.0 mm`.
- `tx_region` is allowed only as non-modeled guide context and must include the required `tx_reference_line` ratios; active-shaped synthetic fixtures use the 720.0 mm TX guide X span.
- Synthetic TX guide fixtures mirror the active sweep Z reference range `[false, 0.75, 1.0, 65]`.
- Fake RxOnly specs used by entry tests mirror the current `Type2StepSpec` shape, including `non_model_objects`.
- `config.make_step_on_sample=false` manifest는 build-time STEP generation path를 대표한다.
- Expected sampled owner/design-variable order includes TX inner sampled owners such as `modeled_objects.tx_inner_rect_void_coil.void_stack_present`, but excludes fixed TX inner `x_position_ratio`, before RX coil sampled owners.
- Expected sampled owner/design-variable order includes `modeled_objects.tv_aluminum_plate.sheet_present` after the RX coil sampled owners when the source sheet presence range has `count > 1`.
- Synthetic source TOML and `ModeledTxInnerSingleCoilSpec` fixtures must expose `void_stack_present` as a sampled integer owner when build design-variable handoff is under test.
- Active single-coil turn-count sweep fixtures cap sampled upper bounds at one below the former maximum: synthetic RX single-coil `turn_count` uses `2.0..5.0` with `count=4`, embedded sampled TOML uses `[true, 2, 5, 4]`, and non-`turn_count` owners remain unchanged; fixed singleton `turn_count` ranges remain unchanged.
- Active fixed/sweep source fixtures use `modeled_objects.tx_inner_rect_void_coil.layer_count = [true, 1, 1, 1]`, and build design variables exclude layer count.
- Fixed singleton TX guide X ratio must not become a build design variable, while sampled TX guide Y ratio remains exported when `count > 1`.
- Build design variables must not include `modeled_objects_tx_outer_rect_void_coil_*`.
- Build design variables must render TV aluminum sheet presence as a bare integer `0` or `1`.

## Invariants / fail-fast
- Unsupported role sets fail before backend execution.
- RxOnly build tests must not require EM-active TX modeled objects.
- Geometry-only `tx_inner_single_coil` can accompany RX without activating removed TX outer modeled roles.
- Passive `tv_aluminum_plate` can accompany the active RX/TX-inner role set without being treated as an EM target.
- TX modeled build dependencies, including TX columns paired with RX, must not reach the setup-ready runner.
- Prepared build validation must reject missing or nonzero TX inner X-position compatibility ranges before setup-ready execution.
- Best-effort build tests catch only declared skippable runtime exceptions; unsupported role validation remains fail-fast before skip recording.
- Worker restart tests assert non-worker exceptions are not retried and persistent worker failures re-raise after the bounded restart limit; failure-path tests monkeypatch the production limit down to three restarts.
- Worker startup tests must distinguish process start-event staggering from AEDT readiness serialization.
- Skipped validation or AEDT setup failures are not persistent-worker restart candidates; they are reported through the skip ledger and then raised by the entry boundary.

### Build resume contract covered here
- `_is_resume_ready_type2_build()`의 조건을 실무 계약으로 검증: 
  - `aedt_path` 파일 또는 exact `<target>.aedt.done` marker가 존재하면 resume-ready로 간주한다.
  - imported ledger 파일이 없거나 imported ledger JSON의 `source_step_ledger_path`, `aedt_path`, `imported_ledger_path`가 현 design 경로와 불일치해도 runner/exporter를 호출하지 않는다.
  - `aedt_path` 파일과 exact marker가 모두 없으면 best-effort가 정상 빌드 경로로 runner를 실행해 완료 artifact를 새로 생성한다.

## Collaborators
- [build.py](../../entry/build.py.md)
- [type2_runtime.py](../../src/peetsfea/type2_runtime.py.md)
- [type2_step_spec.py](../../src/peetsfea/type2_step_spec.py.md)
- [0.2.24 Type2 TX Outer Void Stack](../../../plans/0.2.24-type2-tx-outer-void-stack.md)
- [0.2.24-view-step-gui-setup-ready](../../../plans/0.2.24-view-step-gui-setup-ready.md)
- [0.2.24-type2-tx-region-y-1800-x-reference-fixed](../../../plans/0.2.24-type2-tx-region-y-1800-x-reference-fixed.md)
- [0.2.24-type2-turn-count-sweep-upper-bound](../../../plans/0.2.24-type2-turn-count-sweep-upper-bound.md)
- [0.2.24-type2-batch-resume-absolute-sample-index](../../../plans/0.2.24-type2-batch-resume-absolute-sample-index.md)
- [0.2.25 Type2 Exported Body Bounds Import Validation](../../../plans/0.2.25-type2-exported-body-bounds-import-validation.md)
- [0.2.25 Type2 TV Aluminum Sheet Presence](../../../plans/0.2.25-type2-tv-aluminum-sheet-presence.md)
