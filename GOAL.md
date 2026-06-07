---
title: GOAL
created: 2026-06-01
updated: 2026-06-07
tags:
  - goal
  - 0.3.0
---

# 0.3.0 추가 목표: RX spiral 지원

0.3.0의 기본 형상은 TX/RX SSW 코일이다.

이번 추가 목표는 RX에 한해서 `coilmaker.py`의 normal/spiral 경로를 다시 사용할 수 있게 하는 것이다. 이 경로는 fallback이 아니라 TOML에서 명시적으로 선택한 RX 형상 모드다.

## 계약

- TX는 계속 SSW 코일로 고정한다.
- RX만 `IS_SSW_ENABLED = false`일 때 spiral 경로를 사용한다.
- `NO_SSW_QTURN_START_INT`, `NO_SSW_QTURN_N_INT`는 `coilmaker.py`의 `SpiralCoilParameters` 의미를 그대로 따른다.
- RX spiral 선택과 quarter-turn 값은 `coil_making_token.toml` action token에 보존한다.
- RX spiral이 지원되지 않거나 검증에 실패하면 SSW나 placeholder로 대체하지 않고 즉시 raise한다.

## 성공 조건

- `examples/0.3.0_fixed.toml`과 `examples/0.3.0_sweep.toml`에 RX spiral 관련 필드가 있다.
- RX spiral 선택 시 생성 결과가 표준 TOML token으로 재현 가능하다.
- 기본값은 TX/RX SSW 상태를 유지한다.
