---
title: test_generate_type2_step.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 21:47
tags:
  - tests
  - type2
  - export
---

# test_generate_type2_step.py

## Source
- Path: `tests/type2/test_generate_type2_step.py`
- Code note path: `sdd/code/tests/type2/test_generate_type2_step.py.md`

## 역할
- type2 parser/export/ledger contract regression을 검증한다.

## Canonical coverage
- `tx_plate_stack` / `rx_plate_stack` parser acceptance
- object id mismatch / coil-only field rejection
- TX/RX exact 34-body contract
- TX full `tx_region` YZ + `min_x` anchor
- RX full `rx_region_max` YZ + `min_x` anchor
- `terminal_metadata = {"kind": "none"}` export contract

## 변경 시 주의점
- active example role drift와 exact-name order drift를 같은 테스트 층에서 잡아야 한다.
