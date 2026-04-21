---
title: test_type2_tx_turns.py
created: 2026-04-21 @ 00:00
updated: 2026-04-22 @ 01:10
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
- 정규화된 TX 평면 2D 거리(`normalized_tx_plane_distances`) 가중치와 시리즈/패럴렐 `equivalent_turn_count` 기반 group allocation 규칙의 순수 Python 계약을 검증한다.

## 입력 / 출력
- `normalized_tx_plane_distances`, `turn_weights`, `allocate_series_turns`, `allocate_parallel_turns`, `resolve_tx_turns`의 입력-출력 불변성을 점검한다.
- 패럴렐/시리즈 모두 equivalent-turn target-budget group allocation 결과를 출력 턴 벡터로 검증한다.
- 실패 케이스(비양수 가중치, series total cap 위반, parallel branch turn cap/불가능한 harmonic equivalent)를 커버한다.
- geometry renderer가 넘기는 `max_turn_count` cap을 series/parallel allocator가 지키는지 검증한다.

## Canonical coverage
- 가중치 음수/0 즉시 실패.
- series 3x3 `equivalent_turn_count=31`은 `sum(turns) <= 31`일 때만 유효하다.
- series `equivalent_turn_count`가 coil_count 미만이거나 31 초과면 fail-fast한다.
- parallel 3x3 `equivalent_turn_count=1/9`는 모든 branch를 1턴으로, `10/9`는 모든 branch를 10턴으로 만든다.
- parallel 3x3 `equivalent_turn_count=4.0`은 branch cap 때문에 fail-fast한다.
- 연결 모드별 래퍼 동작.
- geometry turn cap: series/parallel 모두 overflow를 fail-fast로 처리한다.

## 변경 시 주의점
- `equivalent_turn_count`의 mode별 feasibility 제약이 바뀌면 fail-fast assertion 문구를 동기화해야 한다.
- series/parallel allocator의 branch cap이나 lower-bound contract가 바뀌면 기대 턴 벡터를 함께 갱신해야 한다.
