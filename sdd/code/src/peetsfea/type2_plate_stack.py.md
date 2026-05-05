---
title: type2_plate_stack.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - rx
  - plate-stack
---

# type2_plate_stack.py

## Source
- Path: `src/peetsfea/type2_plate_stack.py`
- Code note path: `sdd/code/src/peetsfea/type2_plate_stack.py.md`
- Status: active

## 역할
- RX plate-stack scene data generation helper다.
- Previous TX plate-stack shape and array contracts are removed from SDD for the 0.2.24 reset.

## Canonical state
- RX plate-stack output remains exact and deterministic.
- RX terminal metadata may feed RxOnly port setup.

## Invariants / fail-fast
- Invalid RX geometry dimensions fail immediately.
- Do not document TX plate-stack arrays or TX body names here during the reset.

## Collaborators
- [0.2.22-type2-rx-plate-stack](../../../plans/0.2.22-type2-rx-plate-stack.md)
- [0.2.22-type2-rx-plate-stack-striped-copper](../../../plans/0.2.22-type2-rx-plate-stack-striped-copper.md)
