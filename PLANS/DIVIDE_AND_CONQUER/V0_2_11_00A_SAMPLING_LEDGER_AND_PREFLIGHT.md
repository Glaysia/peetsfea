# V0.2.11-00A Sampling Ledger And Preflight

## 상태/목적
- 상태: Planned
- 목적: 독립 샘플링 자유도를 `SamplingRegistry`와 `SamplingLedger`로 단일화하고, hidden dimension을 preflight에서 조기에 차단한다.
- 이번 문서는 설계 원장과 소유권 규칙을 정의하며 실제 코드 변경은 아직 수행하지 않는다.
- dataset/repro public contract는 `00C`에서 정의한다.

## 핵심 계약
- 모든 독립 샘플링 자유도는 정확히 하나의 canonical owner만 가진다.
- registry entry는 최소한 아래 정보를 가진다.
  - `canonical_key`
  - `owner_path`
  - `sampler_kind`
  - `value_type`
  - `export_to_dataset`
  - `replay_affects_design`
- alias/derived path는 owner를 가질 수 없고 canonical entry만 참조한다.
- 예: `coil_shape.tx_vertical.outer_x`는 `coil_shape.tx_dd.outer_x`의 derived alias로만 선언한다.

## 공통 샘플링 API
- `{range}` 기반 scalar 선택은 registry 기반 선택 함수로 통합한다.
- `coil_groups.count_mode`, `coil_groups.count_range`, `coil_groups.count_fixed`는 공통 API로 흡수한다.
- `pcbs[*].present`는 공통 API로 흡수한다.
- `relative_to_pcb`의 `z_delta_path`도 registry owner를 통해 선택한다.
- 공통 API 밖 `build_candidates()` / `sample_candidate()` 직접 호출은 금지한다.

## 비범위
- `dataset.toml` export shape
- `repro.toml` freeze/export contract
- uniform seedset ordering contract
- ferrite spec path, geometry, adaptive defaults

## Preflight/Audit 규칙
- spec 전체를 순회해 sample-like field를 전수 스캔한다.
- 각 필드는 반드시 아래 셋 중 하나여야 한다.
  - canonical sampled field
  - declared derived alias
  - non-effective 또는 fixed field이며 `count=1`
- 아래는 preflight 즉시 실패 대상이다.
  - unknown sampled field
  - duplicate ownership
  - normalized-away variable field
  - hidden dimension
- fixed-topology에서 normalize로 소거되는 값은 `count>1`을 허용하지 않는다.
- `tx_opt_*`, `rx_opt_*`의 `present`처럼 설계에 영향을 주지 않는 샘플링은 버그로 간주한다.

## 테스트 축
- registry completeness test
- unknown sampled field failure
- duplicate owner failure
- normalized-away sampled field failure

## 수용 기준
- 이 문서만 읽어도 독립 샘플링 자유도의 canonical ownership 규칙을 결정할 수 있다.
- sample-like field가 registry/alias/fixed 셋 중 어디에 속해야 하는지 명확하다.
- hidden dimension과 normalized-away variable이 허용되지 않는다는 점이 문서상 분명하다.
