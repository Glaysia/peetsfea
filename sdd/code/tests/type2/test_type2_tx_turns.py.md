---
title: test_type2_tx_turns.py
created: 2026-04-21 @ 00:00
updated: 2026-04-21 @ 23:14
tags:
  - tests
  - type2
  - tx
---

# test_type2_tx_turns.py

## Source
- Path: `tests/type2/test_type2_tx_turns.py`
- Code note path: `sdd/code/tests/type2/test_type2_tx_turns.py.md`
- Related owner: `[[sdd/code/src/peetsfea/type2_tx_turns.py]]`

## 역할
- 정규화된 `|x|` 가중치와 시리즈/패럴렐 턴 배분 규칙의 순수 Python 계약을 검증한다.

## 입력 / 출력
- `normalized_x_distances`, `turn_weights`, `allocate_series_turns`, `allocate_parallel_turns`, `resolve_tx_turns`의 입력-출력 불변성을 점검한다.
- 패럴렐/시리즈 모두 total-budget largest-remainder 결과를 출력 턴 벡터로 검증한다.
- 실패 케이스(비양수 가중치, series 합 부족, `parallel_total_turn_count < coil_count`)를 커버한다.
- geometry renderer가 넘기는 `max_turn_count` cap을 series/parallel allocator가 지키는지 검증한다.

## Canonical coverage
- 가중치 음수/0 즉시 실패.
- 시리즈 1턴 seed + largest-remainder 결과 정합성.
- 패럴렐 total-budget largest-remainder 분배 정합성(3x3 total=36 -> 각 4턴, 1x1 total=36 -> 36턴).
- 연결 모드별 래퍼 동작.
- geometry turn cap: series/parallel 모두 overflow를 fail-fast로 처리한다.

## 변경 시 주의점
- total-budget 계약(`sum(n_i) == *_total_turn_count`)이 바뀌면 기대 턴 벡터를 함께 갱신해야 한다.
- `parallel_total_turn_count`의 정수/하한 제약이 바뀌면 fail-fast assertion 문구를 동기화해야 한다.
