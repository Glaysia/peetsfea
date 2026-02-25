# PHASE7 - Radiation 영역/경계 + TX/RX 포트

## 목표
- 해석 필수 전처리: radiation 영역/경계와 TX/RX lumped port를 생성한다.
- 해당 단계를 공용 EM 파이프라인(`boundary_port` 단계)으로 표준화한다.

## 범위
- 단계 진입 조건:
  - selection hard-check 통과 케이스만 boundary/port 단계에 진입
- Radiation:
  - 모델 bbox 기준 `±3500mm` region
  - radiation boundary 지정
- Port:
  - TX/RX 체인 시작점 근처 리드 연장
  - 포트 2D 면 생성 후 lumped port (`port_tx`, `port_rx`)
  - 포트 방향 산출은 `em_context` 기반 일반화(타입별 하드코딩 금지)
- 메타데이터:
  - `ports` 필드

## 실패 규약
- region/boundary/port 생성 실패 시 즉시 hard fail
- 포트 단계 실패 로그에 원인과 그룹 path(`coil_shape.<kind>.*`, `coil_spacing.*`)를 포함
