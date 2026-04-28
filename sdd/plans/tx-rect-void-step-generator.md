---
title: Type2 TX Rect/Void Modeled Object
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - tx-rect-void
  - step-export
---

# Type2 TX Rect/Void Modeled Object

## Goal
- `tx_rect_void`를 standalone TOML workflow가 아니라 `examples/type2_fixed.toml`의 첫 modeled object role로 다룬다.
- 기존 standalone geometry fields는 `type2_fixed.toml`의 `[[modeled_objects]]` entry로 흡수한다.
- 기존 `tx_rect_void` geometry authoring code는 implementation detail로 재사용할 수 있지만, 앞으로 public SSOT는 `type2_fixed.toml`이다.

## Scope
- 포함:
  - `examples/type2_fixed.toml`
  - `[[modeled_objects]] role = "tx_single_coil"`
  - tx rect/void geometry parameters
  - terminal metadata
  - object-level STEP + metadata ledger output
- 제외:
  - 제거된 standalone coil TOML을 새 public input으로 계속 확장하는 작업
  - AEDT EM ports, source assignment, solve
  - generic multi-coil family 설계
  - global placement transform

## Decisions
- `tx_single_coil`의 first geometry family는 rect/void route-around coil이다.
- `type2_fixed.toml`의 modeled object entry가 object identity, role, model_state, material, geometry parameters, terminal path를 소유한다.
- standalone coil TOML은 더 이상 tracked public input이나 test fixture로 남기지 않는다.
- type2 v1 TX coil은 단층만 지원하며 exported copper는 fused single body여야 한다.
- type2 v1 single-coil export는 terminal stub를 centerline 양끝에 추가하며, current implementation에서는 stub 길이를 TOML의 `terminal_stub_length_mm`가 소유한다.
- future canonical single-coil contract에서는 explicit `terminal_stub_length_mm` 대신 derived `layer_gap_mm * 0.8` stub semantics로 이동한다.
- generated metadata ledger는 `type2_fixed.toml`에서 파생되어야 하며, standalone TOML path를 canonical source로 기록하지 않는다.
- v1 terminal path는 matching corner만 허용한다: `A_cw_to_a`, `B_ccw_to_b` 같은 `<outer>_<cw|ccw>_to_<inner>` 형식.
- `void`는 copper 금지 keepout이며, generated copper box가 void와 면적으로 겹치면 즉시 실패한다.
- 이 object stage는 still no EM ports, no sources, no solve다.

## Affected Notes
- 관련 상위 계획: [0.2.22-type2-step-to-em-validate-pipeline](0.2.22-type2-step-to-em-validate-pipeline.md)
- 관련 단일화 계획: [0.2.22-type2-toml-unification](0.2.22-type2-toml-unification.md)
- 관련 completed baseline: [0.2.22-type2-build123d-non-model-step](0.2.22-type2-build123d-non-model-step.md)
- 관련 import/setup 방향: [0.2.22-type2-step-to-em-validate-pipeline](0.2.22-type2-step-to-em-validate-pipeline.md)

## Acceptance
- `tx_rect_void`는 SDD 계획에서 standalone public workflow가 아니라 `type2_fixed.toml` modeled object로 설명된다.
- `type2_fixed.toml`에서 생성되는 metadata JSON은 modeled object identity, role, model_state, canonical coordinates, material, terminal-path metadata를 담는다.
- metadata JSON은 expected exported body names/count를 담고, 기본 expected bodies는 `tx_pcb_l0`, `tx_copper_l0`이다.
- canonical coordinates와 exported copper bbox는 terminal stub가 내려가는 하단 길이까지 포함한다.
- invalid TOML, invalid range, unsupported terminal path, layer gap below 2mm, copper/void overlap은 조용히 넘어가지 않고 예외를 발생시킨다.
- current public modeled-object schema is implementation-era state and is expected to change in the generalized-engine / TX multilayer phase.
