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
- 패럴렐 greedy 결과와 tie-break 결정을 출력 턴 벡터로 검증한다.
- 실패 케이스(비양수 가중치, series 합 부족, 패럴렐 타깃 과대/과소)도 커버한다.

## Canonical coverage
- 가중치 음수/0 즉시 실패.
- 시리즈 1턴 seed + largest-remainder 결과 정합성.
- 패럴렐 greedy reciprocal-error 개선량 및 결정성 tie-break(aggregate error, share error, 가중치, 인덱스).
- 개선량 동률에서 `가중치 우선`, 가중치까지 동률이면 `낮은 인덱스 우선`을 고정한다.
- 연결 모드별 래퍼 동작.

## 변경 시 주의점
- 패럴렐 분배는 현재 패턴의 tie-break 규칙을 전제한다.
- 가중치/타깃 범위 조정 시 테스트 기대값이 직접 변경되어야 한다.
