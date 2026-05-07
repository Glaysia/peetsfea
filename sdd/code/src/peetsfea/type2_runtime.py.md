---
title: type2_runtime.py
created: 2026-04-18 @ 09:09
updated: 2026-05-07 @ 00:00
tags:
  - runtime
---

# type2_runtime.py

## Source
- Path: `src/peetsfea/type2_runtime.py`
- Code note path: `sdd/code/src/peetsfea/type2_runtime.py.md`
- Status: active

## 역할
- type2 build/runtime orchestration helper다.
- 0.2.24 SDD 기준 active default path is RxOnly setup-ready.
- 선택된 호출 경로에서 setup-ready 이후 EM solve/report export까지 실행할 수 있다.
- Prepared build 집합의 STEP ledger를 AEDT runner 전에 보장한다.

## 입력 / 출력
- 입력: sampled design metadata, build options, output paths
- 출력: generated STEP/AEDT/EM artifacts, explicit build-skip ledger entries for best-effort batch build,
  or fail-fast exception

## Canonical state
- RxOnly build path does not require TX modeled geometry.
- `tx_region` may flow as non-modeled guide context only.
- Setup-ready role validation accepts the active RX modeled role set, the active RX plus `tx_inner_single_coil`
  set, and either set with one passive `tv_aluminum_plate` modeled body.
- Build prep must not pass TX modeled sampled design variables to the backend.
- EM solve mode uses the same prepared build and setup-ready runner, then exports the active RX output report.
- A manifest entry's `step_ledger_path` is canonical for build input; if it exists, validate and reuse it, and if it is missing, regenerate it from the sampled TOML.
- Default batch build can request per-design best-effort attempts. In that path, each design owns its STEP generation and AEDT setup attempt, and skippable `ValueError`/`RuntimeError` failures are recorded as explicit build skipped entries.
- Parallel best-effort output is reassembled in prepared-build input order before returning artifacts and skipped entries.
- Default best-effort batch build treats a prepared design as already complete when its STEP ledger validates, `aedt_path` exists, and `imported_ledger_path` exists with a valid JSON payload whose `source_step_ledger_path`, `aedt_path`, and `imported_ledger_path` all match the current prepared build paths, so interrupted batches can resume without rebuilding completed sampled TOMLs.
- Related plan: [0.2.24-type2-batch-resume-absolute-sample-index](../../../plans/0.2.24-type2-batch-resume-absolute-sample-index.md).

## Invariants / fail-fast
- Unsupported role sets fail before backend execution; `tx_outer_single_coil` is rejected by the active runtime gate.
- Runtime failures are fail-fast unless the caller explicitly requests skip-recording for validation/infeasible sample attempts or default build-batch continuation.
- Build skipped entries preserve `design_id`, `seed`, `sampled_toml_path`, coarse failure phase, exception type, and exception message.
- Best-effort build only catches `ValueError` and `RuntimeError`; structural errors such as type errors, missing files outside the skippable generation path, and assertion failures still abort.
- Resume reuse is allowed only after STEP ledger validation; partial outputs without AEDT, without imported ledger, with malformed imported-ledger JSON, or with mismatched path fields are retried by running the normal setup-ready runner.
- EM solve failures raise and do not downgrade to setup-ready success.
- Invalid existing STEP ledger or missing scene STEP raises instead of overwriting silently.

## Collaborators
- [type2_sampled.py](type2_sampled.py.md)
- [type2_step_export.py](type2_step_export.py.md)
- [type2_step_em_solve.py](backend/pyaedt/type2_step_em_solve.py.md)
- [type2-step-to-em-validate-pipeline](../../../architecture/type2-step-to-em-validate-pipeline.md)
- [0.2.24-view-step-gui-setup-ready](../../../plans/0.2.24-view-step-gui-setup-ready.md)
