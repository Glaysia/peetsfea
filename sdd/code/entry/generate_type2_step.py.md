---
title: generate_type2_step.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 19:20
tags:
  - type2
  - step-export
---

# generate_type2_step.py

## Source
- Path: `entry/generate_type2_step.py`
- Code note path: `sdd/code/entry/generate_type2_step.py.md`
- Related plan: [[sdd/plans/0.2.22-type2-toml-unification]]
- Related umbrella plan: [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]]
- Related feature plan: [[sdd/plans/0.2.22-type2-tx-underlay-mull12060ferrite]]
- Related architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]
- Related test: [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 역할
- `examples/type2_fixed.toml`을 단일 type2 authoring input으로 읽는다.
- `[[non_model_objects]]`와 `[[modeled_objects]]`를 모두 하나의 canonical scene STEP(`type2_scene.step`) 안에 넣어 export한다.
- generated scene STEP 결과와 retained metadata handoff를 ledger(`type2_step_ledger.json`)로 기록한다.
- direct single-coil CLI consumers can export the modeled `tx_single_coil` object from the same type2 TOML without using a standalone TOML input, while the full ledger path supports both TX/RX single-coil entries together.
- modeled single-coil placement는 owner plane별로 절대 배치를 계산하며, terminal stub/bus 포함 높이를 normal-axis height에 포함한다.
- placement는 routing envelope가 아니라 derived modeled bbox를 기준으로 계산한다.
- current implementation delegates to the generalized single-coil core and consumes TX multilayer parallel-bus outputs directly.
- entry-facing modeled export contract keeps port-sheet ownership in `terminal_metadata.port_sheet_vertices_xyz` only and never reintroduces port-sheet STEP bodies.
- TX underlay milestone adds scene-layer explicit tri-layer solids below the TX modeled stack while keeping underlay responsibility outside the `tx_rect_void` core.
- the entry surface fail-fast validates expected body names/count for single-layer TX/RX and TX multilayer before returning the ledger to callers.
- the entry surface fail-fast validates the metadata-owned port-sheet geometry rule:
  - the sheet lies in the shared plane of the two canonical owner bottom faces
  - TX always uses the two bottom bus faces, with single-layer TX synthesizing the same bus footprint from its one-layer terminal-stub column; RX uses the two terminal-stub bottom-face squares
  - the sheet boundary is built from one widened canonical diagonal on each owner bottom-face square
  - each owner diagonal is chosen against the inter-owner centerline: among the two square diagonals, keep the one whose endpoints maximize the summed perpendicular distance to the line joining the two owner centers
  - the exported sheet resolves to exactly four unique vertices, one diagonal endpoint pair per owner square
  - single-square-owned geometry, unwidened diagonal selection, and terminal-pair span geometry are not accepted anymore

## 입력 / 출력
- 입력: `examples/type2_fixed.toml`
- 출력 디렉터리 기본값: `run/step/type2`
- 출력 artifact:
  - `run/step/type2/type2_scene.step`
  - `run/step/type2/metadata/<object_id>.metadata.json` (modeled objects only)
  - `run/step/type2/type2_step_ledger.json`
- CLI entry: `.venv/bin/python entry/generate_type2_step.py`

## Canonical state
- module-level mutable state는 없다.
- canonical 입력은 `type2_fixed.toml`의 object registry다.
- canonical export ledger는 `type2_step_ledger.json`이며 AEDT geometry reverse-calculation 없이 생성 시점 metadata를 유지한다.
- canonical artifact path는 ledger top-level `scene_step_path`가 소유한다.
- canonical retained boundary-policy field는 ledger top-level `em_policy`다.
- non-model ledger section is a single combined-scene owner that records the member object ids.
- combined non-model ledger entry also records `member_objects` with per-object canonical coordinates so the type2 modeled export can derive `tx_region` placement metadata without reopening TOML.
- active example `type2_fixed.toml` baseline is data-owned: the scene is globally Z-rebased so `tx_region.bottom == 0`, and the generator must preserve that explicit world-coordinate contract instead of renormalizing it.
- modeled object ledger entries are metadata-only; per-entry `step_path`는 없다.
- modeled object metadata keeps `source_toml_path` as the type2 TOML path even though the internal `tx_rect_void` parser is reused.
- TX modeled metadata keeps per-layer PCB names plus a single `tx_copper_stack` expected body name when multilayer, terminal points resolve to the two bottom bus faces for the multilayer case, and `port_sheet_vertices_xyz` resolves from TX bus bottom faces for every supported TX layer count.
- TX modeled metadata keeps `underlay_repeat_count` ownership in the source TOML and reflects the realized underlay only through exact expected body names/count:
  - `tx_underlay_ferrite_u{n}`
  - `tx_underlay_pet_psa_u{n}`
  - `tx_underlay_air_u{n}`
- type2 owns modeled placement: exported modeled metadata is already scene-absolute and matches each role's owner-plane contract using the derived PCB+copper union bbox (`tx_region` centered/top-aligned XY, `rx_region_actual` bottom-Z/right-face-aligned YZ).
- modeled scene authoring passes the same role profile through realization, box decomposition, placement, and final scene export.
- port-sheet vertices are modeled metadata, not non-model members, and remain outside the final `type2_scene.step` child set.
- TX underlay placement is scene-layer owned: the first ferrite top face touches the modeled canonical minimum-Z plane and every later unit stacks downward in deterministic tri-layer order.
- port-sheet geometry is defined from the canonical start/end owner pair bottom-face squares: the exported metadata must bridge the two widened diagonals in their shared plane, chosen by maximum perpendicular spread away from the inter-owner centerline.

## Invariants / fail-fast
- `design.units`는 `mm`여야 한다.
- `non_model_objects`, `modeled_objects`는 각각 non-empty array of tables여야 한다.
- object id는 non-model/modeled 합쳐 중복되면 안 된다.
- non-model object는 `primitive=box`, `present=true`, `non_model=true`, valid plane, positive `size_xyz`를 만족해야 한다.
- active type2 export는 object-level multi-STEP가 아니라 하나의 `type2_scene.step`만 만들어야 한다.
- legacy `type2_non_model_scene.step`, `type2_combined_preview.step`, `objects/` 출력은 generator가 정리해야 한다.
- combined non-model scene ledger must preserve member-level canonical coordinates for downstream import placement/styling.
- type2 export must contain exactly one placement owner member per modeled role (`tx_region`, `rx_region_actual`) and use it as the sole absolute-placement source for that role.
- active example rebase is owned by TOML data, not by generator logic. export/runtime must not apply an extra implicit Z normalization pass.
- modeled object role은 현재 `tx_single_coil`, `rx_single_coil`만 허용한다.
- prototype modeled object ids는 role별 canonical id (`tx_rect_void_coil`, `rx_rect_void_coil`)와 일치해야 하며 `material = composite`를 강제한다.
- modeled object는 `model_state=true`여야 한다.
- modeled object range/terminal fields 누락 또는 타입 위반은 즉시 실패한다.
- modeled object uses `outer_y_mm`; ratio-based outer-y input is no longer accepted.
- `outer_x_mm` / `outer_y_mm` are routing-envelope inputs, not exported PCB size guarantees.
- current modeled object surface still carries `terminal_stub_length_mm`, but geometry ownership is derived from `layer_gap_mm * 0.8`.
- `underlay_repeat_count` is a shared modeled-object field with canonical encoding `[true, 0, 8, 5]`. TX supports the realized set `{0, 2, 4, 6, 8}` and RX currently fail-fast rejects non-zero values.
- `tx_single_coil` may export multilayer parallel-bus geometry; `rx_single_coil` still fail-fast rejects `layer_count != 1`.
- RX/TX modeled realization must never fall back to TX default profile inside the type2 scene export path.
- modeled export must record expected exported body names/count for import smoke validation.
- modeled export must place each single coil at export time according to its owner plane with scene-absolute bounds derived from the actual exported PCB+copper union and plane-aware terminal metadata (`start_point_plane_mm`, `end_point_plane_mm`) already resolved.
- TX multilayer expected body names are `tx_pcb_l{n}` plus `tx_copper_stack`; single-layer TX/RX keep `*_pcb_l0` + `*_copper_l0`.
- TX underlay bodies, when present, must append after the TX PCB/copper base set in exact `ferrite -> pet_psa -> air` per-unit order, and `u0` must be the unit nearest the TX modeled body.
- TX underlay footprint must follow the actual exported TX planar bounds, not `tx_region` full bounds and not a separate margin heuristic.
- port-sheet validation is geometry-aware at the entry boundary: exported metadata vertices must stay on the shared owner bottom-face plane and their boundary must connect the two widened owner-bottom diagonals selected from the inter-owner centerline.
- final scene STEP body names must be unique across non-model + modeled bodies.
- `build123d.export_step()`가 `False`를 반환하면 즉시 예외로 중단한다.

## 직접 의존
- Python 표준 라이브러리: `argparse`, `json`, `pathlib`, `tempfile`, `tomllib`
- 외부 라이브러리: `build123d`
- core geometry reuse: [[sdd/code/src/peetsfea/tx_rect_void.py]]

## 이 파일을 쓰는 곳
- type2 single-scene STEP authoring CLI.
- worker2 import/viewer path가 소비할 type2 artifact producer.

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## TODO
- [ ] tx-only convenience export surface를 role-neutral single-coil convenience surface로 정리한다.
- [ ] generalized single-coil engine이 준비되면 current TX-named delegation/temp TOML bridge를 대체한다.
- [ ] solve-ready slice에서 retained ledger에 port/validate handoff metadata를 추가할지 확정한다.
- [ ] imported exact-name partition and future port adapter에서 underlay body taxonomy와 metadata-driven port-sheet reconstruction ownership을 함께 정리한다.

## 변경 시 주의점
- modeled object schema field를 바꾸면 `type2_fixed.toml`과 테스트 fixture를 함께 갱신한다.
- ledger 필드 shape를 바꾸면 downstream import smoke contract를 함께 갱신한다.
- owner region 크기를 바꿀 때는 stub 포함 coil thickness가 owner normal-axis 안에 계속 들어가는지 테스트와 example 값을 함께 확인한다.
- TX underlay는 `tx_rect_void` core output이 아니라 type2 scene-layer responsibility다. core geometry note와 scene/import notes를 분리해 갱신한다.
- 새 modeled role을 추가할 때는 명시적으로 parser/dispatcher를 확장하고 unsupported role fail-fast를 유지한다.
