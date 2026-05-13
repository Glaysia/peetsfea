---
title: build.py
created: 2026-04-17 @ 09:09
updated: 2026-05-13 @ 00:00
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
- 기본 `build.py` 배치 실행은 sampled design별 STEP 생성과 AEDT setup을 개별 시도하고, skippable 실패는 build skip ledger로 남긴 뒤 batch 내부 처리는 계속하되 CLI 성공으로 숨기지 않는다.
- 기본 `build.py` 배치 실행은 hash-derived `.aedt` filename이 이미 존재하면 해당 sampled design의 AEDT 생성을 건너뛰어 중단된 배치를 재개한다.
- 기본 Type2 batch path retries persistent AEDT worker/session failures by restarting the same manifest after 60 seconds, bounded to the production restart limit.
- The restart path uses an injectable sleep callback so tests can avoid waiting on real time.
- Related plan: [0.2.24-type2-batch-resume-absolute-sample-index](../../plans/0.2.24-type2-batch-resume-absolute-sample-index.md).
- `--debug` GUI build uses the attached-HFSS setup path and skips AEDT `ValidateDesign()` because that AEDT call can hang in GUI debug sessions; repository pipeline validation and project save remain active.

## Invariants / fail-fast
- Default batch build records per-design `ValueError`/`RuntimeError` as explicit build skips, writes the skip ledger, then raises from the entry boundary when skips remain.
- Debug build and solve failures raise immediately; setup-ready success is not treated as EM success.
- RxOnly build does not require TX modeled geometry.
- Existing STEP ledgers are validated and reused; missing STEP ledgers are generated before AEDT setup.
- The generated build skip ledger is written beside the manifest as `type2_build_skipped.json` so stale skip state is overwritten on every default build run.
- Resume reuse is filename-only for AEDT artifacts: the hash-derived target `.aedt` path must already exist. The imported ledger is not required for the skip decision.
- Changed TOML content resolves to a different `design_id` and `.aedt` filename, so it is not treated as completed and builds normally.
- Only `Type2AedtWorkerProcessError` is restartable; validation, stale artifact, and coordinate drift failures remain fail-fast.
- The production restart limit is intentionally high for large AEDT batch runs; tests monkeypatch the limit down to keep failure-path coverage fast.
- Builds that create zero AEDT artifacts because all designs were skipped are hard failures, not successful no-op runs.

## Graph links
- Primary owner: [type2-em-setup-boundary](../../architecture/type2-em-setup-boundary.md)
- Direct runtime handoff: [type2_runtime.py](../src/peetsfea/type2_runtime.py.md)
- Representative verification: [test_build_type2_entry.py](../tests/type2/test_build_type2_entry.py.md)
- Related plan: [0.2.25 Type2 Exported Body Bounds Import Validation](../../plans/0.2.25-type2-exported-body-bounds-import-validation.md)
