# Goal: `tx_under_coil` Spiral Serial-Coil Contract

0.3.0 SSW contract에 세 번째 modeled object로 `role = "tx_under_coil"`를 추가한다. 이 object는 TX main coil과 직렬로 연결되는 under-coil copper이며, 별도 독립 코일이나 별도 포트 대상이 아니다. 핵심 구현 대상은 새 코일 형상이 아니라 TX main coil과 under-coil 사이의 직렬 연결이다.

`tx_under_coil` 구현은 새 geometry generator, simple placeholder, ad-hoc bridge, bespoke proxy를 만들지 않는다. 기존 평면 normal spiral coil 생성 경로를 그대로 재사용해서, 같은 종류의 코일을 방향과 위치만 under-coil 배치에 맞게 바꾸어 결정론적으로 생성한다. `tx_under_coil`은 항상 `is_ssw_enabled = false`인 normal spiral 경로만 사용하며, SSW 생성, twist 기반 도체 분할, SSW 포트 anchor 계산 대상이 아니다.

## Reference Geometry

`examples/under_coil.step`는 under-coil 배치와 연결 의도의 기준 예시다. 이 파일은 CadQuery 기준 단일 solid이고 bbox는 대략 `X -9.0..81.14`, `Y -81.07..81.07`, `Z 234.0..290.0`이다.

STEP 내부 entity name과 AEDT entity name은 아직 `tx_ssw_coil_ssw_copper`로 남아 있다. 따라서 이 이름은 semantic source of truth가 아니다. 기준은 기존 평면 normal spiral과 같은 코일을 under-coil 방향/위치에 놓고, TX main coil과 직렬 연결하는 의도다.

구현은 기존 spiral coil 파라미터와 생성 경로를 재사용해야 한다. `examples/under_coil.step`를 새로운 3D helical/freeform coil generator 요구로 해석하면 안 된다. 단순히 별도 bridge body를 붙인 임시 형상도 이 contract를 만족하지 않는다. 연결은 최종 copper topology와 token/ledger 의미에서 TX main coil과 under-coil이 직렬 도체로 이어지도록 처리해야 한다.

## Public Surface

`role = "tx_under_coil"` object surface는 아래 field로 고정한다.

- `is_under_coil_enabled`
- `width_ratio`
- `height_ratio`
- `turn_n_int`
- `gap_ratio`
- `void_area_ratio`
- `void_profile`
- `no_ssw_qturn_start_int`
- `no_ssw_qturn_n_int`

`no_ssw_qturn_start_int = 0`, `no_ssw_qturn_n_int = 0`은 고정값이다. sampled/free owner가 아니며, design-space free owner 집계에 들어가면 안 된다.

`tx_under_coil`의 free owner는 실제 under-coil 형상에 영향을 주는 7개 field만 포함한다.

## Serial TX Contract

`is_under_coil_enabled = true`이면 `tx_under_coil`은 TX main coil의 직렬 도체 일부로 취급한다. 별도 under-coil 포트 1쌍을 만들지 않고, TX/RX 포트 수와 리포트 흐름은 기존 계약을 유지한다.

Under-coil enabled 상태에서는 TX ferrite sheet가 생성되면 안 된다. `tx_under_coil` copper가 존재하는 설계에서 TX ferrite sheet가 함께 생성되는 결과는 invalid contract다.

결과 artifact는 `coil_making_token.toml`, scene STEP, step ledger, AEDT imported geometry, TX/RX port/report flow에서 under-coil 존재와 TX 직렬 연결 의미를 보존해야 한다.

## Fail-Fast Requirements

`is_under_coil_enabled = true`인데 아래 조건 중 하나라도 성립하지 않으면 즉시 raise한다. 대체 경로, degraded geometry, silent skip, log-and-continue는 허용하지 않는다.

- 기존 평면 normal spiral 생성 경로로 `tx_under_coil` copper를 생성하지 못함
- `tx_under_coil` 방향/위치가 under-coil 배치 계약을 만족하지 못함
- STEP 또는 ledger에서 `tx_under_coil` semantic identity가 보존되지 않음
- TX main coil과 under-coil의 직렬 도체 계약이 성립하지 않음
- under-coil 독립 포트가 생성됨
- under-coil enabled 상태에서 TX ferrite sheet가 생성됨

## Acceptance Criteria

- `role = "tx_under_coil"` modeled object가 정확히 1개 있어야 한다.
- `tx_under_coil`은 항상 기존 평면 normal spiral 경로만 사용하고, 방향/위치만 under-coil 배치에 맞게 바꾼다.
- `no_ssw_qturn_start_int`와 `no_ssw_qturn_n_int`는 `0/0` 고정값이며 free owner에 포함되지 않는다.
- Design-space identity/hash는 under-coil realized 값 변화를 반영한다.
- Headless STEP 생성 시 under-coil copper body가 ledger와 STEP에 모두 존재한다.
- STEP/AEDT semantic ledger는 내부 legacy name이 아니라 `tx_under_coil` 의미를 기준으로 copper를 인식한다.
- TX/RX 포트 계약은 기존 포트 수를 유지하고, under-coil 독립 포트는 생기지 않는다.
- Under-coil enabled 설계에서는 TX ferrite sheet가 존재하지 않는다.
