---
title: build.py
created: 2026-04-17 @ 09:09
updated: 2026-05-07 @ 00:00
tags:
  - entry
  - build
---

# build.py

## Source
- Path: `entry/build.py`
- Code note path: `sdd/code/entry/build.py.md`
- Status: active
- Primary graph owner: [type2-em-setup-boundary](../../architecture/type2-em-setup-boundary.md)

## 역할
- sampled type2 design을 build/setup-ready runtime으로 넘기는 entrypoint다.
- 0.2.24 SDD 기준 RxOnly setup-ready path가 active target이다.
- `--solve` 옵션으로 setup-ready 생성 직후 active HFSS setup을 해석하고 report CSV를 export한다.
- Manifest의 `config.make_step_on_sample`와 entry STEP 경로를 기준으로, solve/debug runner 실행 전에 STEP ledger를 보장한다.
- 기본 `build.py` 배치 실행은 sampled design별 STEP 생성과 AEDT setup을 개별 시도하고, skippable 실패는 build skip ledger로 남긴 뒤 나머지 design을 계속 처리한다.
- 기본 `build.py` 배치 실행은 이미 완료된 sampled TOML의 AEDT/import ledger를 재사용해 중단된 배치를 재개한다.
- Related plan: [0.2.24-type2-batch-resume-absolute-sample-index](../../plans/0.2.24-type2-batch-resume-absolute-sample-index.md).
- `--debug` GUI build uses the attached-HFSS setup path and skips AEDT `ValidateDesign()` because that AEDT call can hang in GUI debug sessions; repository pipeline validation and project save remain active.

## Invariants / fail-fast
- Default batch build records per-design `ValueError`/`RuntimeError` as explicit build skips and continues.
- Debug build and solve failures raise immediately; setup-ready success is not treated as EM success.
- RxOnly build does not require TX modeled geometry.
- Existing STEP ledgers are validated and reused; missing STEP ledgers are generated before AEDT setup.
- The generated build skip ledger is written beside the manifest as `type2_build_skipped.json` so stale skip state is overwritten on every default build run.
- Resume reuse requires both AEDT output and imported ledger; partial output remains rebuild work.

## Graph links
- Primary owner: [type2-em-setup-boundary](../../architecture/type2-em-setup-boundary.md)
- Direct runtime handoff: [type2_runtime.py](../src/peetsfea/type2_runtime.py.md)
- Representative verification: [test_build_type2_entry.py](../tests/type2/test_build_type2_entry.py.md)
