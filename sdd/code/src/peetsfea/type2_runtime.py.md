---
title: type2_runtime.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
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
- 출력: generated STEP/AEDT/EM artifacts or fail-fast exception

## Canonical state
- RxOnly build path does not require TX modeled geometry.
- `tx_region` may flow as non-modeled guide context only.
- Setup-ready role validation accepts the active RX modeled role set and the active RX plus geometry-only `tx_inner_single_coil` set.
- Build prep must not pass TX modeled sampled design variables to the backend.
- EM solve mode uses the same prepared build and setup-ready runner, then exports the active RX output report.
- A manifest entry's `step_ledger_path` is canonical for build input; if it exists, validate and reuse it, and if it is missing, regenerate it from the sampled TOML.

## Invariants / fail-fast
- Unsupported role sets fail before backend execution.
- Runtime failures are fail-fast unless the caller explicitly requests skip-recording for validation/infeasible sample attempts.
- EM solve failures raise and do not downgrade to setup-ready success.
- Invalid existing STEP ledger or missing scene STEP raises instead of overwriting silently.

## Collaborators
- [type2_sampled.py](type2_sampled.py.md)
- [type2_step_export.py](type2_step_export.py.md)
- [type2_step_em_solve.py](backend/pyaedt/type2_step_em_solve.py.md)
- [type2-step-to-em-validate-pipeline](../../../architecture/type2-step-to-em-validate-pipeline.md)
