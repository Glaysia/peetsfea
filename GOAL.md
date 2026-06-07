---
title: GOAL
created: 2026-06-01
updated: 2026-06-07
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

### 3. `from_ansys.step` 수동 보정 형상을 배치 기준으로 삼는다

`run/ssw_0_3_0_fixed/from_ansys.step`은 0.3.0 장면 배치의 현재 참조 형상이다. 이 STEP을 그대로 소스 오브 트루스로 삼는 것이 아니라, 사용자가 AEDT에서 수동으로 보정한 시각적/공간적 계약을 코드 생성 경로에 반영한다.

참조 STEP에서 확인한 body 구성은 다음과 같다.

- `tv`: TV non-model body. YZ 평면에 서 있으며, `AEDT_Translucency_V1 = 0.6`.
- `tx_region`: TX 쪽 non-model body. 현재 참조 STEP에서는 `Box1` 이름으로 남아 있지만, 코드 생성 경로에서는 의미 있는 이름인 `tx_region`을 사용한다. material은 `vacuum`, `AEDT_Translucency_V1 = 0.2`.
- `rx_ssw_coil_*`: RX SSW coil body. TV 내부의 YZ 평면에 배치한다.
- `tx_ssw_coil_*`: TX SSW coil body. TV 아래 공간의 XY 평면에 배치한다.

코일 방향 계약은 다음과 같다.

- RX는 YZ 평면에 놓고, 포트가 있는 쪽이 TV 뒷면을 향하게 한다.
- TX는 XY 평면에 놓고, 포트가 있는 쪽이 아래면을 향하게 한다.
- TX/RX 모두 길쭉한 coil height 방향은 Y축 방향으로 둔다.
- TX와 RX를 같은 평면에 정렬하지 않는다. RX는 TV 내부 평면, TX는 TV 아래 공간 평면을 사용한다.

참조 STEP에서 읽은 주요 bounding box는 다음과 같다.

- `tv`: min `(0.0, -921.0, 340.0)`, max `(9.0, 921.0, 1395.0)`, size `(9.0, 1842.0, 1055.0)`.
- `rx_ssw_coil_ssw_copper`: min `(-0.07, -144.07, 339.93)`, max `(3.55, 144.07, 484.07)`, size `(3.62, 288.14, 144.14)`.
- `tx_ssw_coil_ssw_copper`: min `(0.0, -144.105, 236.31)`, max `(144.14, 144.035, 239.93)`, size `(144.14, 288.14, 3.62)`.
- `tx_region` 참조 bbox: min `(0.07, -144.035, 170.0)`, max `(144.14, 144.035, 239.86)`, size `(144.07, 288.07, 69.86)`.

`tx_region`은 현재 참조 STEP의 `Box1`처럼 coil 주변에 가까운 크기로 두지 않는다. 0.3.0 구현에서는 이 body를 coil-tight box가 아니라 TX가 놓일 수 있는 최대 non-model envelope로 키운다. TX coil은 그 최대 envelope 안에 들어가야 하며, TX non-model envelope가 작아서 유효한 TX 배치 공간을 잘라내면 안 된다.

## 성공 조건

- 기본 생성 출력 디렉터리에 `coil_making_token.toml`이 생성된다.
- `coil_making_token.toml`은 표준 TOML로 parse 가능하다.
- token trace는 같은 입력과 seed에서 결정적으로 재생성된다.
- token trace 안에 config, dimension derivation, SSW trace construction, copper/FR4 part creation, boolean operation, STEP export 의미가 보존된다.
- 0.3.0 기본 형상은 SSW 코일이며, normal coil이나 minimal two-port placeholder로 조용히 대체하지 않는다.
- 생성된 STEP에서 non-model object는 AEDT/OCP 확인용으로 투명하게 보인다.
- RX는 TV 내부 YZ 평면에 있고, 포트 방향은 TV 뒷면 기준으로 맞는다.
- TX는 TV 아래 공간의 XY 평면에 있고, 포트 방향은 아래면 기준으로 맞는다.
- TX/RX의 길쭉한 height 방향은 Y축 방향이다.
- TX non-model body는 coil-tight box가 아니라 최대 TX 배치 envelope다.
- 실패한 validation, unsupported geometry, PyAEDT `False` return은 즉시 raise한다.
- 기본 구현과 검증은 headless를 유지한다.

## 이번 범위 밖

- transformer 모델 학습 자체
- 대규모 dataset generation 정책 확장
- GUI AEDT 검증
- legacy `type1`/old `type2` 형상 경로 복구
- token TOML 외의 추가 직렬화 포맷
