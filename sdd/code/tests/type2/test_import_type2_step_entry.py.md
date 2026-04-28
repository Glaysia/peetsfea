---
title: test_import_type2_step_entry.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - test
  - import
---

# test_import_type2_step_entry.py

## Source
- Path: `tests/type2/test_import_type2_step_entry.py`
- Code note path: `sdd/code/tests/type2/test_import_type2_step_entry.py.md`
- Status: active

## 역할
- `entry/import_type2_step.py` import-only behavior를 검증한다.

## Canonical state
- Import-only records imported ownership and object names.
- `tx_region` may pass through as non-modeled guide context.
- Import-only creates no mesh, boundary, ports, or reports.

## Invariants / fail-fast
- Missing RX imported bodies fail immediately.

## Collaborators
- [import_type2_step.py](../../entry/import_type2_step.py.md)
