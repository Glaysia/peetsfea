---
title: test_generate_type2_step.py
created: 2026-04-17 @ 09:09
updated: 2026-04-19 @ 00:25
tags:
  - step-export
---

# test_generate_type2_step.py

## Source
- Path: `tests/type2/test_generate_type2_step.py`
- Code note path: `sdd/code/tests/type2/test_generate_type2_step.py.md`
- Related code: [[sdd/code/entry/generate_type2_step.py]]
- Related plan: [[sdd/plans/0.2.22-type2-toml-unification]]
- Related feature plan: [[sdd/plans/0.2.23-type2-underlay-region-footprint-tx-gap-rx-support]]
- Related feature plan: [[sdd/plans/0.2.23-type2-tx-wall-parallel-ferrite-stack]]
- Related feature plan: [[sdd/plans/0.2.23-type2-ferrite-underlay-equivalent-thickness]]

## 역할
- `generate_type2_step.py`의 type2 parser와 single scene export 계약을 pure-Python pytest로 검증한다.
- fixed example parse path, sweep example parse path, active fixed example export path를 함께 확인한다.
- active/shared `[outputs]` parser와 retained step ledger `outputs` serialization도 함께 검증한다.
- modeled TX/RX single-coil export가 derived modeled bbox 기준으로 owner region 안에 배치되고 canonical scene STEP/ledger에 absolute metadata를 남기는지 확인한다. TX는 `tx_region.min_x` touch를, RX는 owner max-X touch를 본다.

## 입력 / 출력
- 입력:
  - repository examples `examples/type2_fixed.toml`, `examples/type2_sweep.toml`
  - test-local minimal type2 TOML fixtures
- active export example `examples/type2_fixed.toml` 그대로 when export runtime is exercised
- 출력:
  - `tmp_path` 아래 generated `type2_scene.step`, metadata JSON, ledger JSON
  - pytest assertions only (no AEDT launch, no solve)

## Canonical state
- module-level mutable state는 없다.
- canonical fixture는 `_type2_spec_text()`가 만드는 minimal unified type2 TOML이다.

## Invariants / fail-fast
- example `type2_fixed.toml`은 6 non-model + 2 modeled objects로 파싱되어야 하며 underlay/gap/sample fields가 single-candidate로 고정돼야 한다.
- companion example `type2_sweep.toml`은 같은 registry shape를 유지하면서 underlay/sample fields가 canonical sweep ranges를 유지해야 한다.
- TX-only `wall_parallel_stack_present` example contract도 fixed/sweep companion pair에서 각각 fixed `1` / canonical `[true, 0, 1, 2]`를 유지해야 한다.
- both example paths must also parse the full retained legacy-type1 `outputs` contract.
- active example baseline regression은 global Z rebase 결과를 직접 검증해야 한다. `tx_region.bottom == 0`, environment/rx region은 같은 relative spacing을 유지한 채 같이 내려가야 한다.
- export runtime regression은 active example 그대로를 사용하고, copper body label expectation은 realized layer count에 맞춰 결정한다. TX floor-underlay labels는 resolved `underlay_repeat_count`와 무관하게 scene body expectation에 포함되지 않는다.
- duplicate object id는 즉시 실패해야 한다.
- missing `outputs`, unsupported `outputs` key, empty output-variable list, duplicate output-variable name, invalid output-variable name은 즉시 실패해야 한다.
- unsupported modeled role은 즉시 실패해야 한다.
- modeled required field 누락(`terminal_path`)은 즉시 실패해야 한다.
- invalid terminal path는 modeled export 단계에서 즉시 실패해야 한다.
- scene `build123d.export_step()`가 `False`면 즉시 실패해야 한다.
- 성공 케이스에서는 `type2_scene.step` 1개, metadata JSON, ledger JSON이 생성되고 ledger top-level `scene_step_path`, `em_policy`, `outputs`, non-model `member_objects`, modeled expected body names/count, scene-absolute placement/terminal metadata가 기록되어야 한다.
- current regression explicitly covers scene STEP/ledger placement bounds and realized body naming without assuming TX multilayer example input.
- TX placement regression should assert `tx_region.min_x` touch + centered Y + owner max-Z touch.
- generated `type2_scene.step`의 modeled PCB/copper body pair는 final exported solids 기준으로 shared volume이 없어야 한다.
- single-layer scene regression must assert scene labels do not include `tx_port_sheet` or `rx_port_sheet`; STEP exports only PCB/copper bodies.
- next underlay contract regression must assert:
  - TX `underlay_repeat_count`는 floor-parallel `tx_underlay_*` labels를 다시 만들지 않는다
  - RX `underlay_repeat_count = 0`이면 underlay labels가 없다
  - RX `underlay_repeat_count = 2`이면 expected body names 뒤에 collapsed effective `u0` tri-layer labels만 append된다
  - RX `underlay_repeat_count = 8`이면 body count는 늘지 않고 각 ferrite/PET/air thickness만 `8x`로 커진다
- RX underlay body semantic order is geometry contract: each effective family must emit `ferrite -> pet_psa -> air`, and the explicit `air` body must be modeled as exported `vacuum`, not spacing-only omission.
- TX wall-stack placement regression should assert `tx_region.min_x` wall contact + `+X` growth + `tx_region` full Y span + remaining-space Z ownership.
- RX underlay placement regression should assert `rx_region_max` full footprint + `-X` boundary anchor + coil-facing ferrite.
- single-layer scene regression should still confirm the metadata-owned canonical port-sheet polygon stays on the shared terminal-stub bottom-face plane, contains exactly four unique vertices, and bridges the two widened terminal-stub bottom-square diagonals chosen by maximum perpendicular spread away from the inter-stub centerline.
- terminal metadata must also persist canonical `port_sheet_vertices_xyz` that match the expected sheet geometry so downstream HFSS reconstruction can reuse the exact face polygon without relying on STEP sheet bodies.
- TX port-sheet metadata path is supported across single-layer and multilayer TX: regression should assert that the canonical four vertices are derived from the two bottom bus faces rather than expecting a fail-fast gap.
- future test obligations:
  - TX/RX shared generalized-engine parity regression
  - RX still fail-fast rejects multilayer after the first TX multilayer milestone
  - role-aware underlay parse/export regression across both single-layer TX and `tx_copper_stack` multilayer TX

## 직접 의존
- `pytest`
- [[sdd/code/entry/generate_type2_step.py]]

## 이 파일을 쓰는 곳
- default pytest collection.

## 관련 테스트
- 이 파일 자체.

## 변경 시 주의점
- type2 TOML field 이름을 바꾸면 fixture text와 assertion field path를 함께 갱신한다.
- ledger shape를 바꾸면 이 테스트와 downstream import tests를 함께 갱신한다.
- retained `outputs` contract를 바꾸면 example TOML, setup-ready tests, import-ledger tests를 함께 갱신한다.
- RX underlay exact-name order와 body count, TX wall exact-name order를 바꾸면 export/import test notes를 같이 갱신한다. `underlay_repeat_count`가 effective thickness multiplier인지 repeated body count인지 drift시키면 scene/import 계약이 동시에 깨진다.
