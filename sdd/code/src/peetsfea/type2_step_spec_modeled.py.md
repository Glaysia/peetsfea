---
title: type2_step_spec_modeled.py
created: 2026-04-20 @ 00:00
updated: 2026-04-28 @ 00:00
tags:
  - spec
  - modeled
---

# type2_step_spec_modeled.py

## Source
- Path: `src/peetsfea/type2_step_spec_modeled.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_spec_modeled.py.md`
- Status: active

## 역할
- type2 modeled-object parsing and validation helper다.
- 0.2.24 SDD 기준 active documented shape path는 RX modeled roles다.

## 입력 / 출력
- 입력: modeled object TOML tables
- 출력: validated modeled object specs

## Canonical state
- RX single-coil and RX plate-stack parsing remain documented.
- TX modeled roles are not documented as active shape contracts during the reset.
- `tx_region` remains outside modeled parsing as future guide context.

## Invariants / fail-fast
- Unsupported modeled roles/fields fail during parse.
- RxOnly must parse without requiring TX modeled roles.

## Collaborators
- [type2_step_spec.py](type2_step_spec.py.md)
- [type2_step_spec_types.py](type2_step_spec_types.py.md)
