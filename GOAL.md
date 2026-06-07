---
title: GOAL
created: 2026-06-01
updated: 2026-06-01
tags:
  - goal
  - 0.3.0
---

# 0.3.0 단기 목표

0.3.0부터 형상 생성의 기준은 `step-only`에서 검증한 trace-first, action-token-first 방식으로 전환한다.

목표는 단순히 STEP 형상을 만드는 것이 아니다. 입력 TOML과 seed에서 출발해 형상 생성의 의미 있는 행동 단위를 먼저 token stream으로 만들고, 그 token을 재사용 가능한 TOML 산출물로 저장한 뒤, 마지막 단계에서만 STEP/AEDT용 형상으로 렌더링하는 구조를 만든다.

## 핵심 목표

### 1. 출력물에 형상 생성 토큰 TOML을 추가한다

샘플링/생성 결과물에는 STEP, manifest, dataset/repro 계열 산출물과 함께 형상 생성 토큰 TOML이 포함되어야 한다.

이 TOML은 디버그 로그가 아니라 정식 산출물이다. 나중에 transformer 계열 모델 입력으로 사용할 수 있도록, 형상 생성 과정의 의미 단위를 순서 있는 action token으로 보존한다.

기본 파일명은 `coil_making_token.toml`을 사용한다.

토큰 TOML의 기본 계약은 다음과 같다.

- 같은 입력 TOML, 같은 seed, 같은 버전이면 같은 token 순서를 만든다.
- token payload는 scalar, tuple/list, stable ref string 중심으로 구성한다.
- CadQuery, PyAEDT, dataclass instance 같은 Python runtime object를 token payload에 직접 넣지 않는다.
- 부모/자식 관계는 object pointer가 아니라 stable id/ref로 표현한다.
- renderer용 내부 geometry token은 둘 수 있지만, transformer 입력의 기준은 action token TOML이다.
- token TOML 저장은 STEP 렌더링/AEDT import 이전에 수행한다.

예상 흐름은 다음 순서를 따른다.

```text
authoring TOML + seed
-> validated spec
-> deterministic sampled parameters
-> lazy action token stream
-> materialized action trace
-> coil_making_token.toml
-> renderer-private geometry tokens
-> STEP geometry
-> AEDT import/setup
```

### 2. 0.3.0부터 SSW 코일을 사용한다

0.3.0의 활성 형상 생성 목표는 최소 두 포트 placeholder가 아니라 SSW 코일 기반 형상이다.

SSW 코일은 전체 금속 튜브를 만든 뒤 gap을 빼는 방식으로 만들지 않는다. 남길 copper trace를 먼저 정의하고, 그 trace를 3D copper solid로 변환한다.

SSW 형상 계약은 다음을 기본으로 한다.

- `TURN_N_INT`는 SSW band count로 해석한다.
- `GAP_RATIO`는 SSW pitch 중 gap 비율로 해석한다.
- SSW winding의 active face는 위/아래 PCB 평면이다.
- sidewall은 winding 면이 아니라 위/아래 평면 trace가 같은 edge를 덮는 구간을 잇는 connector로 사용한다.
- SSW copper는 STEP 생성 전에 하나의 의도된 conductor로 정리한다.
- 일반 코일 fallback을 기본 경로로 두지 않는다. SSW가 지원되지 않으면 fail-fast로 멈춘다.

## 성공 조건

- 기본 생성 출력 디렉터리에 `coil_making_token.toml`이 생성된다.
- `coil_making_token.toml`은 표준 TOML로 parse 가능하다.
- token trace는 같은 입력과 seed에서 결정적으로 재생성된다.
- token trace 안에 config, dimension derivation, SSW trace construction, copper/FR4 part creation, boolean operation, STEP export 의미가 보존된다.
- 0.3.0 기본 형상은 SSW 코일이며, normal coil이나 minimal two-port placeholder로 조용히 대체하지 않는다.
- 실패한 validation, unsupported geometry, PyAEDT `False` return은 즉시 raise한다.
- 기본 구현과 검증은 headless를 유지한다.

## 이번 범위 밖

- transformer 모델 학습 자체
- 대규모 dataset generation 정책 확장
- GUI AEDT 검증
- legacy `type1`/old `type2` 형상 경로 복구
- token TOML 외의 추가 직렬화 포맷
