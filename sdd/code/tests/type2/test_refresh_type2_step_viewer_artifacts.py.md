---
title: test_refresh_type2_step_viewer_artifacts.py
created: 2026-04-17 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - step-export
---

# test_refresh_type2_step_viewer_artifacts.py

## Source
- Path: `tests/type2/test_refresh_type2_step_viewer_artifacts.py`
- Code note path: `sdd/code/tests/type2/test_refresh_type2_step_viewer_artifacts.py.md`
- Tested source: [refresh_type2_step_viewer_artifacts.py](../../entry/refresh_type2_step_viewer_artifacts.py.md)

## 역할
- viewer refresh input fixture인 active fixed example이 RxOnly viewer/setup surface를 유지하는지 검증한다.
- fixed example에서 TX modeled object, TX sampled-owner block, TX output variable이 다시 생기면 실패한다.

## 입력 / 출력
- 입력:
  - active `examples/type2_fixed.toml`
- 출력:
  - parsed fixed example assertions

## Canonical state
- active fixed example TOML payload가 canonical assertion surface다.

## Invariants / fail-fast
- fixed example keeps `tx_region` only as guide context.
- fixed example keeps `rx_region_max` and the RX modeled object as active geometry inputs.
- fixed example has no active TX modeled role, no TX sampled-owner blocks, and no output expression referencing `TX_TML`.

## 직접 의존
- [type2-em-report-contract](../../../architecture/type2-em-report-contract.md)
- [0.2.24-type2-rxonly-tx-removal](../../../plans/0.2.24-type2-rxonly-tx-removal.md)

## 이 파일을 쓰는 곳
- default pure-Python regression suite.

## 관련 테스트
- This file is high-level active fixed example coverage for the viewer refresh input contract.

## 변경 시 주의점
- notebook refresh output layout must not be tested by editing notebooks in this worker scope.
- example type2 TOML의 modeled object registry가 바뀌면 RxOnly object id assertions를 같이 갱신한다.
