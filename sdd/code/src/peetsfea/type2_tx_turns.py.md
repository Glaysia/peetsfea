---
title: type2_tx_turns.py
created: 2026-04-21 @ 00:00
updated: 2026-04-21 @ 23:10
tags:
  - src
  - type2
---

# type2_tx_turns.py

## Source
- Path: `src/peetsfea/type2_tx_turns.py`
- Code note path: `sdd/code/src/peetsfea/type2_tx_turns.py.md`
- Related plan: `[[sdd/plans/0.2.22-type2-tx-columns-reset]]`

## 역할
- TX 코일 턴 배분 순수 Python 헬퍼를 제공한다.
- `|x-rx_center_x|` 정규화 가중치 계산과 `connection_mode`에 따른 공통 총 턴수 기반 분배를 결정성 있게 수행한다.
- 입력 수치/좌표를 fail-fast 검증하고 유효하지 않은 상태를 즉시 차단한다.

## 입력 / 출력
- `normalized_x_distances`: 코일 중심 좌표(입력 순서 기준)와 `rx_center_x`를 받아 `|x|` 정규화 거리(0..1) 튜플을 반환한다.
- `turn_weights`: 정규화 거리와 다항식 계수 `a,b,c`로 `w_i = a + b*x_i + c*x_i^2` 가중치 튜플을 반환한다.
- `allocate_series_turns`: 가중치와 `series_total_turn_count`로 최소 1턴 보장을 포함한 라지스트 레마인더 배분 결과를 반환한다. Optional `max_turn_count`는 geometry renderer cap을 보조 검증한다.
- `allocate_parallel_turns`: 가중치와 `parallel_total_turn_count`로 최소 1턴 보장을 포함한 동일한 라지스트 레마인더 배분 결과를 반환한다. Optional `max_turn_count`는 geometry renderer cap을 보조 검증한다.
- `resolve_tx_turns`: `connection_mode`와 관련 턴 값으로, 병렬/직렬 공통 총턴수 계약 allocator를 연결한다.

## Canonical state
- 없음(순수 함수, 입력 값 기반 결정성 계산).

## Invariants / fail-fast
- `|x|` 정규화 분모는 0이면 0 거리 분포로 고정한다.
- 모든 `w_i > 0`을 강제한다.
- `series_total_turn_count >= coil_count` 미달은 즉시 실패한다.
- `parallel_total_turn_count >= coil_count` 미달은 즉시 실패한다.
- 시리즈/패럴렐은 각 코일 1턴 seed 후 남은 턴을 weight 기반 largest-remainder로 분배한다.
- 병렬/직렬 모두 `sum(n_i) == total_turn_count` 및 `n_i >= 1` 계약을 유지한다.
- `max_turn_count`가 주어지면 분배 결과의 각 턴이 이를 초과하면 fail-fast한다.

## 직접 의존
- `math`, `typing` 표준 라이브러리만 사용한다.

## 이 파일을 쓰는 곳
- `tests/type2/test_type2_tx_turns.py`

## 관련 테스트
- `tests/type2/test_type2_tx_turns.py`

## 변경 시 주의점
- 결정성 경계는 정렬 규칙(개선량/가중치/인덱스)에 강하게 바인딩된다.
- `series_total_turn_count`와 `parallel_total_turn_count`의 값 범위를 변경하면 샘플/재생산 계약이 직접 영향받는다.
