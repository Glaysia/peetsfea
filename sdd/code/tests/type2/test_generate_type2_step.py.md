---
title: test_generate_type2_step.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 20:11
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
- example `type2_fixed.toml` parse regression은 active spec의 현재 값(`tx.layer_count=1`, `rx.layer_count=1`)을 그대로 반영한다.
- active example baseline regression은 global Z rebase 결과를 직접 검증해야 한다. `tx_region.bottom == 0`, environment/rx region은 같은 relative spacing을 유지한 채 같이 내려가야 한다.
- export runtime regression은 active example 그대로를 사용하고, copper body label expectation은 realized layer count에 맞춰 결정한다.
- duplicate object id는 즉시 실패해야 한다.
- unsupported modeled role은 즉시 실패해야 한다.
- modeled required field 누락(`terminal_path`)은 즉시 실패해야 한다.
- invalid terminal path는 modeled export 단계에서 즉시 실패해야 한다.
- scene `build123d.export_step()`가 `False`면 즉시 실패해야 한다.
- 성공 케이스에서는 `type2_scene.step` 1개, metadata JSON, ledger JSON이 생성되고 ledger top-level `scene_step_path`, `em_policy`, non-model `member_objects`, modeled expected body names/count, scene-absolute placement/terminal metadata가 기록되어야 한다.
- current regression explicitly covers scene STEP/ledger placement bounds and realized body naming without assuming TX multilayer example input.
- generated `type2_scene.step`의 modeled PCB/copper body pair는 final exported solids 기준으로 shared volume이 없어야 한다.
- single-layer scene regression must assert scene labels include `tx_port_sheet` and `rx_port_sheet`.
- single-layer scene regression must assert those sheet bodies remain distinct top-level exported bodies and do not disappear into copper/PCB naming.
- single-layer scene regression should also confirm the port-sheet face stays on the shared terminal-stub bottom-face plane, exports exactly four unique vertices, and bridges the two widened terminal-stub bottom-square diagonals chosen by maximum perpendicular spread away from the inter-stub centerline.
- current TX multilayer port-sheet path is expected to fail fast until a multilayer sheet contract is implemented; regression should assert that explicit failure rather than papering over it.
- future test obligations:
  - TX/RX shared generalized-engine parity regression
  - RX still fail-fast rejects multilayer after the first TX multilayer milestone
  - expected body name/count assertions update for the two current sheet bodies `tx_port_sheet`, `rx_port_sheet`

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
