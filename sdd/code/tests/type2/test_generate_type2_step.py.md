---
title: test_generate_type2_step.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 19:20
tags:
  - type2
  - step-export
---

# test_generate_type2_step.py

## Source
- Path: `tests/type2/test_generate_type2_step.py`
- Code note path: `sdd/code/tests/type2/test_generate_type2_step.py.md`
- Related code: [[sdd/code/entry/generate_type2_step.py]]
- Related plan: [[sdd/plans/0.2.22-type2-toml-unification]]
- Related feature plan: [[sdd/plans/0.2.22-type2-tx-underlay-mull12060ferrite]]

## 역할
- `generate_type2_step.py`의 type2 parser와 single scene export 계약을 pure-Python pytest로 검증한다.
- example parse path와 active example export path를 함께 확인한다.
- modeled TX/RX single-coil export가 derived modeled bbox 기준으로 owner region 안에 배치되고 canonical scene STEP/ledger에 absolute metadata를 남기는지 확인한다.

## 입력 / 출력
- 입력:
  - repository example `examples/type2_fixed.toml`
  - test-local minimal type2 TOML fixtures
- active example `examples/type2_fixed.toml` 그대로 when export runtime is exercised
- 출력:
  - `tmp_path` 아래 generated `type2_scene.step`, metadata JSON, ledger JSON
  - pytest assertions only (no AEDT launch, no solve)

## Canonical state
- module-level mutable state는 없다.
- canonical fixture는 `_type2_spec_text()`가 만드는 minimal unified type2 TOML이다.

## Invariants / fail-fast
- example `type2_fixed.toml`은 7 non-model + 2 modeled objects로 파싱되어야 한다.
- example `type2_fixed.toml` parse regression은 active spec의 현재 값(`tx.layer_count`, `rx.layer_count`, `tx.underlay_repeat_count`, `rx.underlay_repeat_count`)을 그대로 반영한다.
- active example baseline regression은 global Z rebase 결과를 직접 검증해야 한다. `tx_region.bottom == 0`, environment/rx region은 같은 relative spacing을 유지한 채 같이 내려가야 한다.
- export runtime regression은 active example 그대로를 사용하고, copper body label expectation은 realized layer count에 맞춰 결정한다. TX underlay label expectation은 resolved `underlay_repeat_count`에 맞춰 결정한다.
- duplicate object id는 즉시 실패해야 한다.
- unsupported modeled role은 즉시 실패해야 한다.
- modeled required field 누락(`terminal_path`)은 즉시 실패해야 한다.
- invalid terminal path는 modeled export 단계에서 즉시 실패해야 한다.
- RX `underlay_repeat_count != 0`은 modeled export 단계에서 즉시 실패해야 한다.
- scene `build123d.export_step()`가 `False`면 즉시 실패해야 한다.
- 성공 케이스에서는 `type2_scene.step` 1개, metadata JSON, ledger JSON이 생성되고 ledger top-level `scene_step_path`, `em_policy`, non-model `member_objects`, modeled expected body names/count, scene-absolute placement/terminal metadata가 기록되어야 한다.
- current regression explicitly covers scene STEP/ledger placement bounds and realized body naming without assuming TX multilayer example input.
- generated `type2_scene.step`의 modeled PCB/copper body pair는 final exported solids 기준으로 shared volume이 없어야 한다.
- single-layer scene regression must assert scene labels do not include `tx_port_sheet` or `rx_port_sheet`; STEP exports only PCB/copper bodies.
- TX underlay regression must assert:
  - `underlay_repeat_count = 0`이면 underlay labels가 없다
  - `underlay_repeat_count = 2`이면 TX expected body names 뒤에 exact 6 underlay labels가 append된다
  - `underlay_repeat_count = 8`이면 upper-bound body count와 deterministic `u0..u7` ordering이 유지된다
- TX underlay body order is geometry contract: each unit must emit `ferrite -> pet_psa -> air`, and the explicit `air` body must be modeled as exported `vacuum`, not spacing-only omission.
- TX underlay placement regression must assert the first ferrite top face touches TX canonical minimum-Z and all later units stack downward from that plane while sharing the same TX planar footprint.
- single-layer scene regression should still confirm the metadata-owned canonical port-sheet polygon stays on the shared terminal-stub bottom-face plane, contains exactly four unique vertices, and bridges the two widened terminal-stub bottom-square diagonals chosen by maximum perpendicular spread away from the inter-stub centerline.
- terminal metadata must also persist canonical `port_sheet_vertices_xyz` that match the expected sheet geometry so downstream HFSS reconstruction can reuse the exact face polygon without relying on STEP sheet bodies.
- TX port-sheet metadata path is supported across single-layer and multilayer TX: regression should assert that the canonical four vertices are derived from the two bottom bus faces rather than expecting a fail-fast gap.
- future test obligations:
  - TX/RX shared generalized-engine parity regression
  - RX still fail-fast rejects multilayer after the first TX multilayer milestone
  - TX underlay parse/export regression across both single-layer TX and `tx_copper_stack` multilayer TX

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
- TX underlay exact-name order와 body count를 바꾸면 export/import test notes를 같이 갱신한다.
