---
title: GOAL
created: 2026-06-01
updated: 2026-06-07
tags:
  - goal
  - 0.3.0
---

# 0.3.0 추가 목표: RX spiral 및 MULL ferrite sheet 지원

0.3.0의 기본 형상은 TX/RX SSW 코일이다.

이번 추가 목표는 RX에 한해서 `coilmaker.py`의 normal/spiral 경로를 다시 사용할 수 있게 하는 것이다. 이 경로는 fallback이 아니라 TOML에서 명시적으로 선택한 RX 형상 모드다.

추가로 TX/RX 코일 영역의 normal-axis 잔여 공간에 MULL ferrite sheet를 각각 한 장씩 배치한다. 두 sheet는 하나의 공유 비율 자유변수로 위치를 정한다.

## 계약

- TX는 계속 SSW 코일로 고정한다.
- RX만 `IS_SSW_ENABLED = false`일 때 spiral 경로를 사용한다.
- `NO_SSW_QTURN_START_INT`, `NO_SSW_QTURN_N_INT`는 `coilmaker.py`의 `SpiralCoilParameters` 의미를 그대로 따른다.
- RX spiral 선택과 quarter-turn 값은 `coil_making_token.toml` action token에 보존한다.
- RX spiral이 지원되지 않거나 검증에 실패하면 SSW나 placeholder로 대체하지 않고 즉시 raise한다.
- MULL ferrite sheet 두께는 `0.12 mm`로 고정한다.
- MULL ferrite sheet는 TX/RX 각각 코일 assembly와 같은 in-plane footprint를 가진다.
- `ferrite.mull_position_ratio`는 TX/RX가 공유하는 자유변수이며, `0.0`은 잔여 공간의 바깥쪽 경계, `1.0`은 코일에 가장 가까운 위치를 의미한다.
- TX sheet는 `tx_region.zmin`과 TX coil `zmin` 사이의 잔여 Z 공간에 놓는다.
- RX sheet는 `rx_region_max.xmin`과 RX coil `xmin` 사이의 잔여 X 공간에 놓는다.
- 잔여 공간이 sheet 두께보다 작으면 sheet를 축소하거나 생략하지 않고 즉시 raise한다.

## 성공 조건

- `examples/0.3.0_fixed.toml`과 `examples/0.3.0_sweep.toml`에 RX spiral 관련 필드가 있다.
- `examples/0.3.0_fixed.toml`과 `examples/0.3.0_sweep.toml`에 공유 MULL ferrite 위치 비율 필드가 있다.
- RX spiral 선택 시 생성 결과가 표준 TOML token으로 재현 가능하다.
- MULL ferrite sheet 생성 결과가 ledger와 표준 TOML token에 보존된다.
