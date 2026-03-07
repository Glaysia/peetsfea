# V0.2.11-01 Spec And Policy

## 상태/목적
- 상태: Planned
- 목적: `0.2.11`에서 필요한 스펙 계약과 adaptive policy 기본값 변경을 단일 SSOT 문서로 고정한다.
- 이번 문서는 문서화 전용이며 코드, 테스트, 예제 TOML, 릴리즈 노트 수정은 아직 수행하지 않는다.
- sampling ledger와 replay contract는 `00A/00B/00C`를 전제로 한다.

## 스펙 계약
- 목표 `spec_version`은 `0.2.11`이다.
- ferrite 제어는 단일 전역 flag만 사용한다.
- TOML 경로는 `[ferrite.present]` 로 고정한다.
- TOML 표현은 `range = [true, 0, 1, 2]` 로 고정한다.
- `ferrite.present = 0`이면 RX/TX ferrite는 모두 없다.
- `ferrite.present = 1`이면 RX/TX ferrite는 모두 있다.
- RX/TX 중 하나만 존재하는 모드는 지원하지 않는다.
- 이번 버전에서 함께 고정할 파라미터는 아래와 같다.
  - RX ferrite thickness = `2.4mm`
  - TX ferrite thickness = `4.0mm`
  - relative permeability = `500`

## 정책 기본값
- simulation 기본값 변경은 아래 3개만 포함한다.
  - `percent_refinement = 20`
  - `maximum_passes = 20`
  - `max_delta_s = 0.007`
- 나머지 adaptive 관련 키는 기존 계약을 유지한다.

## 영향 범위
- `run_design`
- resolver constants/api
- manifest types
- example TOML
- default EM policy

## 비범위
- ferrite geometry/metadata 배치 규칙
- dataset/repro export contract
- uniform seedset ordering

## 수용 기준
- 이 문서만 읽어도 `0.2.11`의 새 스펙 경로와 전역 ferrite semantics를 결정할 수 있다.
- 이 문서만 읽어도 변경되는 adaptive 기본값 3개를 확정할 수 있다.
- RX `2.4mm`, TX `4.0mm`, `mu_r=500`이 문서에 명시되어 있다.
- ferrite on/off가 RX/TX를 함께 제어한다는 점이 모호하지 않다.
