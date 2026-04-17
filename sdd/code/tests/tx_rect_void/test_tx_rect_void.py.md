---
title: test_tx_rect_void.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 14:11
tags:
  - type2
  - tx-rect-void
---

# test_tx_rect_void.py

## Source
- Path: `tests/tx_rect_void/test_tx_rect_void.py`
- Code note path: `sdd/code/tests/tx_rect_void/test_tx_rect_void.py.md`
- Related plans: [[sdd/plans/tx-rect-void-step-generator]], [[sdd/plans/0.2.22-type2-single-coil-corner-relief]]
- Related code: [[sdd/code/src/peetsfea/tx_rect_void.py]], [[sdd/code/src/peetsfea/tx_rect_void_geometry.py]]

## 역할
- Type2 rect/void STEP generator의 parser, deterministic realization, geometry, single-layer TX/RX port-sheet scene export, TX multilayer fail-fast gap, fused-body export 계약을 pure-Python pytest로 검증한다.
- AEDT/HFSS launch 없이 build123d STEP export smoke만 수행한다.
- metadata JSON이 registry-aligned `modeled_objects` entry와 expected exported body contract를 포함하는지와 type2 TOML CLI smoke를 함께 검증한다.
- terminal stub가 geometry, bbox, metadata Z bounds에 반영되는지, 그리고 runtime 길이가 `layer_gap_mm * 0.8` derived rule을 따르는지 검증한다.

## 입력 / 출력
- 입력: test-local TOML strings written under pytest `tmp_path`.
- 출력: pytest assertions, temporary STEP and metadata JSON files.

## Canonical state
- module-level runtime state는 없다.
- canonical fixtures는 `_spec_text()`가 생성하는 internal TX rect/void TOML이다.

## Invariants / fail-fast
- missing keys, bad ranges, unsupported terminal path, layer gap below 2mm는 즉시 실패해야 한다.
- supported corner/direction terminal paths는 blunt centerline을 만들어야 하며,
  적어도 하나 이상의 45도 beveled segment를 포함해야 한다.
- same-corner terminal path는 type1-derived planner를 사용해 outer terminal을 next-ring 좌표로 seed해야 한다.
- debug `boxes` regression은 layer별 `planar_outline` AABB 1개와 terminal stub 2개 구조를 검증한다.
- layer primitive regression은 authoring feature set이 `planar_segment + terminal_stub` 뿐인지 확인해 separate corner-join path 재도입을 막는다.
- join regression은 representative corner에서 segment polygon이 naive endpoint가 아니라 offset-line intersection join vertex를 직접 포함하는지 검증한다.
- terminal stub boxes는 layer마다 2개여야 하고, trace width의 60% 정사각형 단면과 `derived_stub + pcb + copper` 높이를 가져야 한다.
- TX multilayer는 두 vertical bus box를 추가한 debug decomposition까지는 유지해야 한다.
- exported PCB/copper body pair는 final STEP scene에서 shared volume이 없어야 한다.
- single-layer TX/RX STEP scene은 각각 `tx_port_sheet` / `rx_port_sheet`를 별도 face body로 포함해야 한다.
- single-layer export metadata expected body names/count는 port sheet label까지 포함해야 한다.
- single-layer port-sheet regression은 sheet face가 두 terminal stub의 shared bottom-face plane과 평행하고 그 plane에 그대로 놓이는지 검증해야 한다.
- single-layer port-sheet regression은 두 stub center를 잇는 직선을 기준으로 각 terminal stub bottom-face square에서 endpoint들의 perpendicular-distance 합이 더 큰 diagonal이 선택되는지 검증해야 한다.
- single-layer port-sheet regression은 exported sheet boundary가 그 widened diagonal 둘을 edge로 포함하고, 나머지 두 edge가 stub-to-stub bridge인지 확인해야 한다.
- TX `layer_count=2`는 box decomposition과 union bounds 계산은 유지하되, current port-sheet path에서는 즉시 실패해야 한다.
- RX `layer_count=2` 또는 `3`은 shared engine path를 타더라도 즉시 실패해야 한다.
- STEP scene은 debug copper segment가 여러 개여도 single-layer TX/RX는 `*_pcb_l0` + `*_copper_l0` + `*_port_sheet` body set만 가져야 한다.
- notebook-scale RX single-layer example도 exported body로는 `rx_pcb_l0`, terminal stub까지 fuse된 `rx_copper_l0`, `rx_port_sheet`만 가져야 한다.
- initial port-sheet milestone은 coil당 single sheet contract이며 TX multilayer sheet generation은 follow-up 전까지 expected fail-fast gap이다.
- non-adjacent planar segment strip이 겹치면 turn-to-turn short로 즉시 실패해야 한다.
- export smoke는 non-empty STEP과 metadata JSON을 생성해야 한다.
- metadata JSON은 single modeled object entry의 identity, role, model_state, expected body names/count, canonical coordinates, terminal metadata를 포함해야 하고 canonical bounds는 actual exported body union, Z bounds는 stub 하단까지 포함해야 한다.
- explicit placement offset을 주는 export는 boxes와 modeled metadata를 같은 absolute offset으로 평행이동해야 한다.
- future test obligations:
  - generalized TX/RX single-coil engine parity regression beyond current role-specific fail-fast split
  - RX export-path fail-fast regression after `entry/generate_type2_step.py` rewiring
  - multilayer TX placement/import/notebook contract regression after later patches

## 직접 의존
- `pytest`
- [[sdd/code/src/peetsfea/tx_rect_void.py]]

## 이 파일을 쓰는 곳
- default pytest collection for the new standalone STEP workflow.

## 관련 테스트
- 이 파일 자체.

## TODO
- [ ] TX/RX direct parity regression을 추가해 같은 terminal path에서 blunt corner count, bounds, placement를 role pair로 검증한다.
- [ ] bevel 존재 여부를 넘어서 actual exported solid face topology까지 확인하는 regression을 검토한다.

## 변경 시 주의점
- TOML schema나 geometry semantics를 바꾸면 fixture builder와 expected failure messages를 같이 갱신한다.
- CLI smoke payload shape가 flat export summary인지 nested modeled-object payload인지 바뀌면 assertions를 함께 갱신한다.
- Real AEDT import test를 이 파일에 넣지 않는다.
