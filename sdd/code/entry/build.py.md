---
title: build.py
created: 2026-04-17 @ 09:09
updated: 2026-06-01
tags:
  - entry
  - build
---

# build.py

- Path: `entry/build.py`
- Code note path: `sdd/code/entry/build.py.md`
- Status: active
- Primary plan: [0.3.0 minimal step two port reset](../../plans/0.3.0-minimal-step-two-port-reset.md)

## 역할
- active 0.3.0 minimal AEDT build and solve entrypoint다.
- Manifest entries from `entry/sample.py` are built through the minimal STEP two-port HFSS facade.

## 입력 / 출력
- 입력:
  - minimal manifest JSON
  - optional selected design ID
  - optional `--solve`
- 출력:
  - `.aedt`
  - `minimal_imported_ledger.json`
  - optional `Output_Variables_Table1.csv`

## Canonical state
- Manifest entries are the complete build queue.

## Invariants / fail-fast
- Missing STEP artifacts are regenerated from the sampled TOML.
- Build and solve stop on the first failed HFSS operation.
- Old type2 worker, retry, debug GUI, and legacy geometry paths are not part of this entrypoint.

## 직접 의존
- [minimal_step.py](../src/peetsfea/minimal_step.py.md)
- [minimal_em.py](../src/peetsfea/backend/pyaedt/minimal_em.py.md)

## 관련 테스트
- [test_minimal_em.py](../tests/backend_em/test_minimal_em.py.md)

## 변경 시 주의점
- Do not reintroduce best-effort continuation or old type2 manifest compatibility.
