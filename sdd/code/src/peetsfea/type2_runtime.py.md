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

## 입력 / 출력
- 입력: sampled design metadata, build options, output paths
- 출력: generated STEP/AEDT artifacts or fail-fast exception

## Canonical state
- RxOnly build path does not require TX modeled geometry.
- `tx_region` may flow as non-modeled guide context only.
- Setup-ready role validation accepts only the active RX modeled role set.
- Build prep must not pass TX modeled sampled design variables to the backend.

## Invariants / fail-fast
- Unsupported role sets fail before backend execution.
- Runtime failures are fail-fast unless the caller explicitly requests skip-recording for validation/infeasible sample attempts.

## Collaborators
- [type2_sampled.py](type2_sampled.py.md)
- [type2_step_export.py](type2_step_export.py.md)
- [type2-step-to-em-validate-pipeline](../../../architecture/type2-step-to-em-validate-pipeline.md)
