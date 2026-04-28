---
title: type2_step_ledger.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - step-export
  - ledger
---

# type2_step_ledger.py

## Source
- Path: `src/peetsfea/type2_step_ledger.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_ledger.py.md`
- Status: active

## 역할
- STEP export handoff metadata를 JSON ledger로 직렬화한다.
- 0.2.24 SDD 기준 RX modeled handoff와 non-modeled guide/context handoff만 active shape contract다.

## 입력 / 출력
- 입력: exported RX modeled entries, non-modeled guide/context entries, EM policy
- 출력: `type2_step_ledger.json`

## Canonical state
- RX body names/counts/groups are exact export contract values.
- `tx_region` may be present as non-modeled future guide context.
- `tx_region_actual` and TX modeled bodies are not required ledger entries for RxOnly.
- Mesh/boundary/port/report runtime summaries are not ledger-owned.

## Invariants / fail-fast
- Ledger body names must match exported names exactly.
- RxOnly ledger must not require TX modeled bodies.
- Missing RX terminal metadata for RxOnly is a contract failure.

## Collaborators
- [type2_step_export.py](type2_step_export.py.md)
- [type2_step_import_ledger.py](backend/pyaedt/type2_step_import_ledger.py.md)
- [type2-em-report-contract](../../../architecture/type2-em-report-contract.md)
