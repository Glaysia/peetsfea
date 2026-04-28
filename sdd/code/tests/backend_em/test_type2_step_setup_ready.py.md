---
title: test_type2_step_setup_ready.py
created: 2026-04-18 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - test
  - em
---

# test_type2_step_setup_ready.py

## Source
- Path: `tests/backend_em/test_type2_step_setup_ready.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_step_setup_ready.py.md`
- Status: active

## 역할
- setup-ready runtime의 import, mesh, boundary, RX port, RX report assembly behavior를 검증한다.
- 0.2.24 SDD 기준 RxOnly behavior is the active documented target.

## Canonical state
- Tests should verify RX conductor mesh and one RX lumped port.
- Tests should verify RxOnly does not create TX ports or TX output variables.
- Future two-terminal report names are documented in [type2-em-report-contract](../../../architecture/type2-em-report-contract.md) but are not active RxOnly assertions.

## Invariants / fail-fast
- PyAEDT false-return handling remains fail-fast.
- Missing RX terminal metadata must fail.

## Collaborators
- [type2_step_setup_ready.py](../../src/peetsfea/backend/pyaedt/type2_step_setup_ready.py.md)
- [type2-em-report-contract](../../../architecture/type2-em-report-contract.md)
