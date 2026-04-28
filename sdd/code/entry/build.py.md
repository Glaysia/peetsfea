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

## Invariants / fail-fast
- Build failures raise immediately unless explicitly recorded as validation/infeasible sample skips upstream.
- RxOnly build does not require TX modeled geometry.

## Collaborators
- [type2_runtime.py](../src/peetsfea/type2_runtime.py.md)
