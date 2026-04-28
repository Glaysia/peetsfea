---
title: type2_step_spec_types.py
created: 2026-04-20 @ 00:00
updated: 2026-04-28 @ 00:00
tags:
  - spec
  - types
---

# type2_step_spec_types.py

## Source
- Path: `src/peetsfea/type2_step_spec_types.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_spec_types.py.md`
- Status: active

## 역할
- type2 spec dataclasses, constants, and helper type aliases를 소유한다.

## Canonical state
- RX modeled role constants remain active.
- `tx_region` guide constants may remain as non-modeled context.
- TX shape role constants are not active SDD contracts during the 0.2.24 reset.

## Invariants / fail-fast
- Runtime state must be concrete and non-null.
- Unsupported active role drift must fail in parser/preflight.

## Collaborators
- [type2_step_spec.py](type2_step_spec.py.md)
