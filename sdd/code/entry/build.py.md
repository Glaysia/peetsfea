---
title: build.py
created: 2026-04-17 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - entry
  - build
---

# build.py

## Source
- Path: `entry/build.py`
- Code note path: `sdd/code/entry/build.py.md`
- Status: active

## 역할
- sampled type2 design을 build/setup-ready runtime으로 넘기는 entrypoint다.
- 0.2.24 SDD 기준 RxOnly setup-ready path가 active target이다.
- `--solve` 옵션으로 setup-ready 생성 직후 active HFSS setup을 해석하고 report CSV를 export한다.
- Manifest의 `config.make_step_on_sample`와 entry STEP 경로를 기준으로, build/solve runner 실행 전에 STEP ledger를 보장한다.

## Invariants / fail-fast
- Build failures raise immediately unless explicitly recorded as validation/infeasible sample skips upstream.
- RxOnly build does not require TX modeled geometry.
- Solve failures raise immediately; setup-ready success is not treated as EM success.
- Existing STEP ledgers are validated and reused; missing STEP ledgers are generated before AEDT setup.

## Collaborators
- [type2_runtime.py](../src/peetsfea/type2_runtime.py.md)
