# Goal: `tx_under_coil`은 TX의 x-min 쪽 YZ 평면 코일이다

`examples/under_coil.step`에는 TX coil이 두 개 있다. 위쪽의 큰 XY 평면 spiral은 TX main coil이고, under-coil이 아니다. under-coil은 global X 방향 영역이 최소인 쪽에 붙어 있는 두 번째 TX coil이다.

따라서 `examples/under_coil.step`를 볼 때 전체 bbox나 위쪽 큰 XY spiral을 under-coil로 해석하면 안 된다. under-coil 기준은 x-min 영역의 얇은 YZ 평면 loop다.

## STEP 확인 기준

`examples/under_coil.step`는 하나의 fused solid로 읽히지만, face/mesh를 x 위치로 보면 under-coil 영역을 분리해서 확인할 수 있다.

- 전체 artifact bbox는 대략 `X -9.0..81.14`, `Y -81.07..81.07`, `Z 234.0..290.0`이다.
- 이 전체 bbox에는 TX main coil과 under-coil이 같이 들어 있으므로 under-coil 방향 판정에 그대로 쓰면 안 된다.
- x-min 쪽 under-coil surface만 보면 대략 `X -9.0..-7.77`, `Y -80.14..81.02`, `Z 234.0..266.55`이다.
- 즉 under-coil은 global X 방향으로 얇고, global Y/Z 방향으로 footprint를 갖는 YZ 평면 coil이다.

## 올바른 형상 의도

- `tx_under_coil`은 TX main coil과 직렬로 연결되는 두 번째 TX coil이다.
- `tx_under_coil`은 독립 coil도 아니고 별도 port 대상도 아니다.
- TX main coil은 기존처럼 XY 평면에 있을 수 있다. 이 XY main coil을 under-coil 오류로 오인하지 않는다.
- under-coil copper는 global X 최소 영역에 배치한다.
- under-coil copper의 local coil 면은 global YZ 평면과 평행해야 한다.
- under-coil normal은 global X 축과 정렬되어야 한다.
- under-coil의 X 방향 두께는 coil/trace 두께 수준으로 얇아야 하고, footprint는 Y/Z 방향으로 펼쳐져야 한다.

## 구현 범위

먼저 under-coil의 semantic 분리와 placement frame/orientation을 바로잡는다. YZ 평면 under-coil 계약을 성립시키는 데 꼭 필요한 경우가 아니면 새 coil topology, extra port, ferrite redesign, sampled-field 변경, type1 유지보수로 범위를 넓히지 않는다.

구현은 가능한 한 기존 normal spiral 생성 경로를 재사용한다. 필요한 변경은 `tx_under_coil`을 TX main coil과 같은 XY plane에 다시 생성하는 것이 아니라, x-min 쪽 YZ plane에 세워서 배치하는 것이다.

## Fail-Fast 요구사항

`is_under_coil_enabled = true`일 때 아래 조건 중 하나라도 성립하면 즉시 raise한다.

- `tx_under_coil`이 TX main coil과 같은 global XY 평면 coil로 생성됨
- `tx_under_coil`이 global X 최소 영역에 배치되지 않음
- `tx_under_coil`의 local coil 면이 global YZ 평면과 평행하지 않음
- `tx_under_coil` normal이 global X와 정렬되지 않음
- 생성된 STEP/ledger에서 `tx_under_coil`과 TX main coil을 구분할 수 없음
- under-coil용 독립 port pair가 생성됨
- TX serial-coil 계약이 깨짐

fallback orientation, silent rotation substitute, degraded geometry, log-and-continue는 허용하지 않는다.

## Acceptance Criteria

- 재생성된 STEP에서 TX main coil과 `tx_under_coil` 두 TX coil을 구분할 수 있어야 한다.
- TX main coil은 under-coil 판정 대상이 아니다.
- `tx_under_coil`은 global X 최소 영역에 있어야 한다.
- `tx_under_coil` bbox는 global X 방향으로 얇고, global Y/Z 방향으로 의도한 footprint를 가져야 한다.
- TX/RX port count는 기존 계약을 유지해야 하며, under-coil 독립 포트가 생기면 안 된다.
- ledger/STEP semantic identity는 legacy internal name이 아니라 `tx_under_coil`을 사용해야 한다.
- AEDT/PyAEDT에 영향을 주는 code change 후에는 real headless AEDT validation을 실행해야 한다.
