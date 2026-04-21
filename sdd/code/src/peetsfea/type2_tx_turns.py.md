---
title: type2_tx_turns.py
created: 2026-04-21 @ 00:00
updated: 2026-04-22 @ 01:10
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
- TX 평면 2D 정규화 거리 가중치 계산과 `connection_mode`에 따른 단일 `equivalent_turn_count` 기반 물리 턴 분배를 결정성 있게 수행한다.
- 입력 수치/좌표를 fail-fast 검증하고 유효하지 않은 상태를 즉시 차단한다.

## 입력 / 출력
- `normalized_tx_plane_distances`: 코일 중심 좌표(입력 순서 기준)와 `rx_center_xyz`를 받아 TX 평면 XY 2D 정규화 거리(0..1) 튜플을 반환한다.
- `turn_weights`: 정규화 2D 거리와 다항식 계수 `a,b,c`로 `w_i = a + b*d_i + c*d_i^2` 가중치 튜플을 반환한다.
- `allocate_series_turns`: 가중치와 전체 체인 `equivalent_turn_count`로부터 반올림된 physical target을 만들고, 최소 1턴 보장과 전체 합 `<= 31` 제약 후 동일거리 그룹 단위 배분 결과를 반환한다. Optional `max_turn_count`는 geometry renderer cap을 보조 검증한다.
- `allocate_parallel_turns`: 각 병렬 branch 정수 턴 `n_i`를 `1..10` 범위에서 선택하고, 병렬 등가 `1 / sum(1 / n_i)`가 요청 `equivalent_turn_count`에 가장 가까운 결과를 반환한다. 동일거리 그룹은 같은 턴수를 유지한다.
- `resolve_tx_turns`: `connection_mode`와 단일 `equivalent_turn_count`로, 병렬/직렬 allocator를 연결한다.

## Canonical state
- 없음(순수 함수, 입력 값 기반 결정성 계산).

## Invariants / fail-fast
- TX 평면 2D 거리 정규화 분모는 0이면 0 거리 분포로 고정한다.
- 동일거리 group key는 normalized distance를 소수점 12자리로 고정 반올림해 산출한다. 이는 대칭 좌표의 부동소수점 미세 차이 때문에 위/아래 tile이 갈라지는 것을 방지하는 canonical grouping 규칙이다.
- 모든 `w_i > 0`을 강제한다.
- Series mode는 `coil_count <= round(equivalent_turn_count) <= 31`을 강제한다.
- Parallel mode는 realized branch별 할당 결과가 `1..10` 턴 범위를 벗어나면 즉시 실패하며, physical turn sum을 등가턴으로 사용하지 않는다.
- 동일 normalized distance는 분모 정규화 후 계산된 float 키로 그룹화한다(허용 오차 없음).
- 시리즈/패럴렐은 각 코일 1턴 seed 후 남은 physical budget을 동일거리 그룹 단위로 분배한다.
- 동일 normalized distance group의 코일들은 항상 같은 turn count를 가져야 한다.
- 직렬은 `sum(n_i) <= 31`과 `n_i >= 1` 계약을 유지한다. 병렬은 `1 / sum(1 / n_i)`의 closest-fit 계약과 `1 <= n_i <= 10` 계약을 유지한다.
- `max_turn_count`가 주어지면 분배 결과의 각 턴이 이를 초과하면 fail-fast한다.

## 직접 의존
- `math`, `typing` 표준 라이브러리만 사용한다.

## 이 파일을 쓰는 곳
- `tests/type2/test_type2_tx_turns.py`

## 관련 테스트
- `tests/type2/test_type2_tx_turns.py`

## 변경 시 주의점
- 결정성 경계는 distance group 구성과 group 정렬 규칙에 강하게 바인딩된다.
- `equivalent_turn_count`는 공개 SSOT이며 mode별 physical budget 변환 규칙이 샘플/재생산 계약이다. 다시 두 public turn owner로 나누면 dataset owner surface가 직접 깨진다.
