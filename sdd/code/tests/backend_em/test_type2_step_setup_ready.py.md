---
title: test_type2_step_setup_ready.py
created: 2026-04-18 @ 09:09
updated: 2026-04-29 @ 00:00
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
- 0.2.24 SDD 기준 `RxOnly` and `TxRx` behavior are active documented targets.
- solve-enabled setup tests verify analysis and report CSV export before desktop release.

## Canonical state
- Tests should verify RX conductor mesh and one RX lumped port.
- Tests should verify RxOnly does not create TX ports or TX output variables.
- Tests should verify TxRx keeps TX inner + RX ledger entries, creates TX/RX port assignments, assembles two-terminal report variables, and meshes TX inner + RX conductors.
- 포트 할당 단위 테스트에 `tx_inner_single_coil` paired mode (`tx_inner_single_coil` + `rx_single_coil`)를 추가로 검증한다.
- The active full setup-ready happy path uses a single `rx_single_coil` modeled entry.
- Future two-terminal report names are documented in [type2-em-report-contract](../../../architecture/type2-em-report-contract.md) but are not active RxOnly assertions.
- Solve/export tests use the same active output-variable report created by setup-ready generation.

## Invariants / fail-fast
- PyAEDT false-return handling remains fail-fast.
- Missing RX/TX terminal metadata or unsupported role pairings must fail with context.

## Collaborators
- [type2_step_setup_ready.py](../../src/peetsfea/backend/pyaedt/type2_step_setup_ready.py.md)
- [type2-em-report-contract](../../../architecture/type2-em-report-contract.md)
