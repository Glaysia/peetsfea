---
title: geometry.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - types
  - geometry
---

# geometry.py

## Source
- Path: `src/peetsfea/types/geometry.py`
- Code note path: `sdd/code/src/peetsfea/types/geometry.py.md`
- Status: active

## 역할
- Shared geometry metadata types를 소유한다.

## Canonical state
- RX endpoint/group metadata remains active.
- TX-specific group kinds are dormant implementation details unless a future TX plan reactivates them.

## Invariants / fail-fast
- Geometry metadata must be explicit and non-null.

## Collaborators
- [type2-em-report-contract](../../../../architecture/type2-em-report-contract.md)
