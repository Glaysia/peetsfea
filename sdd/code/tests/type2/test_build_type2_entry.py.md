---
title: test_build_type2_entry.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
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

## Canonical state
- Build path can reuse existing STEP ledger or generate missing RX STEP artifacts.
- `tx_region` is allowed only as non-modeled guide context.

## Invariants / fail-fast
- Unsupported role sets fail before backend execution.
- RxOnly build tests must not require TX modeled objects.

## Collaborators
- [build.py](../../entry/build.py.md)
- [type2_runtime.py](../../src/peetsfea/type2_runtime.py.md)
