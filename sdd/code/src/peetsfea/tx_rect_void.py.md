---
title: tx_rect_void.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - tx-rect-void
---

# tx_rect_void.py

## Source
- Path: `src/peetsfea/tx_rect_void.py`
- Code note path: `sdd/code/src/peetsfea/tx_rect_void.py.md`
- Related plans: [[sdd/plans/tx-rect-void-step-generator]], [[sdd/plans/0.2.22-type2-single-coil-corner-relief]], [[sdd/plans/0.2.22-type2-multilayer-tx-generic-single-coil]]
- Related docs: [[docs/tx-rect-void-step]]
- Related geometry helpers: [[sdd/code/src/peetsfea/tx_rect_void_geometry.py]]
- Related STEP viewer registry: [[sdd/plans/0.2.22-step-viewer-notebook-registry]]

## 역할
- Type2 modeled `tx_single_coil` / `rx_single_coil` rect/void spec을 읽고, deterministic sampled realization과 build123d STEP export를 수행한다.
- 내부 런타임 타입은 TX 중심 naming 대신 generalized single-coil naming으로 옮겨 가며, role 차이는 `SingleCoilProfile` injection으로 분리한다.
- 기존 type1 PyAEDT/HFSS resolver와 분리된 STEP authoring path만 담당한다.
- metadata JSON에는 `realized`/debug `boxes`, fused STEP body expectation, type2 modeled-object ledger가 되는 `modeled_objects`를 기록한다.
- Type1 neo TX DD에서 해결한 same-corner terminal planner와 outer terminal seed 규칙을 type2 STEP 경로에 적용한다.
- public export path의 canonical centerline은 always-on `45-degree beveled blunt corner`다.
- copper ownership은 blunt centerline 각 segment가 offset-line intersection join vertex를 직접 포함하는 exact joined-strip polygon과 terminal stub prism, 그리고 TX multilayer일 때 두 terminal column vertical bus prism으로 나뉜다.
- `tx_rect_void_geometry.py`가 point/polygon/join math를 맡고, 이 파일은 realization, per-layer primitive assembly, STEP/body/metadata orchestration을 맡는다.
- TX multilayer는 start/end stub column을 각각 full-height bus로 common해서 전체를 2-terminal parallel-connected stack으로 만든다.
- scene export의 canonical geometry source는 validated copper primitive set이며, debug `BoxSpec`은 modeled bounds/metadata 확인용 decomposition이다.
- 코일 양끝에는 trace width의 60% 정사각형 단면을 가지는 downward terminal stub을 붙여 copper body 안에 포함한다.
- runtime stub 길이는 explicit TOML ownership이 아니라 `layer_gap_mm * 0.8` derived rule을 canonical로 사용한다.

## 입력 / 출력
- 입력: `SingleCoilRectVoidSpec`, source TOML path, integer `seed`, output STEP path, metadata JSON path.
- 출력: `SingleCoilRectVoidExportResult`, STEP file, metadata JSON.
- 핵심 함수: `load_tx_rect_void_spec()`, `realize_tx_rect_void_spec()`, `build_tx_rect_void_box_specs()`, `build_tx_rect_void_step_scene()`, `export_tx_rect_void_step_from_spec()`.

## Canonical state
- module-level mutable state는 없다.
- Canonical runtime state는 `RealizedSingleCoilRectVoid` dataclass와 generated `BoxSpec` tuple이다.
- export canonical metadata에는 single-entry `modeled_objects`, expected exported body names/count, canonical coordinates, terminal metadata가 포함된다.
- Sampling owner identity는 TOML path string plus seed hash로 결정된다.
- Centerline canonical state는 type1-derived same-corner seed path를 blunt corner로 변환한 point sequence다. private sharp seed helper는 public export contract가 아니라 shaping 이전 내부 단계다.
- `boxes`는 canonical geometry 자체가 아니라 live copper primitive set에서 파생된 debug AABB decomposition이다.
- canonical copper owner는 joined segment primitive set이고, `boxes`나 separate join filler는 geometry owner가 아니다.
- single-layer/RX scene builder는 layer별 copper fuse를 만들고, TX multilayer scene builder는 전 layer primitive + 두 bus를 하나의 `tx_copper_stack`으로 fuse한다.
- PCB footprint canonical state는 per-layer copper decomposition의 planar bbox에서 파생된다.
- type2 caller가 전달한 placement offset/profile이 있으면 exported boxes, modeled object bounds, terminal plane metadata에 동일한 scene-absolute projection을 적용한다.
- canonical modeled bounds는 routing envelope가 아니라 actual exported PCB+copper union을 기록하며, Z bounds는 terminal stub 하단까지 포함한다.
- TX multilayer terminal metadata canonical point는 raw centerline endpoint가 아니라 두 bus의 bottom-face center다.

## Invariants / fail-fast
- `design.units`는 `mm`이어야 한다.
- range table은 `[is_integer, start, end, count]` 형식이어야 하며, count는 1 이상이어야 한다.
- `outer_y_mm`는 ratio가 아니라 canonical mm 단위 routing-envelope range다.
- `turn_count`는 1..4, `tx_single_coil.layer_count`는 1 이상, `rx_single_coil.layer_count`는 여전히 1이어야 하며 `layer_gap_mm`는 2.0 이상이어야 한다.
- runtime stub 길이는 `layer_gap_mm * 0.8`에서 derive되며 양수여야 한다. TOML의 `terminal_stub_length_mm`는 current parser compatibility field일 뿐 geometry owner가 아니다.
- `metal_fill_factor`는 0.15..0.60이어야 하며 realized trace width는 모든 side에서 0.5mm 이상이어야 한다.
- v1은 centered same-corner route만 지원하므로 void center ratios는 public type2 example에서 0으로 고정한다.
- void bounds는 outer bounds 안에 axis-specific margin을 두고 들어와야 한다.
- blunt centerline은 모든 turn corner에서 45도 beveled segment를 만들어야 하며, same-corner seed/start/end ownership은 바뀌면 안 된다.
- inner corner bevel trim은 void keepout을 침범하지 않도록 줄어들어야 한다.
- generated copper primitive polygon은 void keepout과 면적으로 겹치면 즉시 예외를 발생시킨다.
- non-adjacent planar copper primitive polygon이 겹치면 turn-to-turn short로 간주하고 즉시 예외를 발생시킨다.
- terminal stub는 start/end segment 쪽으로만 약간 겹쳐 단일 fuse solid를 만들고, short 검사는 planar segment들에 대해서만 수행한다.
- TX multilayer vertical bus는 stub planar bbox footprint를 그대로 사용하고, Z span은 lowest stub bottom에서 highest stub top까지여야 한다.
- RX/TX 모두 realized/profile/box decomposition/scene export가 같은 role profile context를 공유해야 한다.
- outer terminal point는 type1 neo TX DD처럼 next-ring coordinate로 seed되어야 하며, outer rectangle corner에 직접 남아 있으면 안 된다.
- planar segment primitive는 axis-aligned 전용이 아니라 blunt centerline segment의 exact joined strip polygon을 사용해야 하며, separate corner join primitive를 다시 도입하면 안 된다.
- polygon overlap helper는 positive-area overlap만 short/void overlap으로 해석해야 하며, edge touch를 overlap으로 넓혀 잡으면 bevel trim/void validation이 다시 흔들린다.
- PCB layer box는 realized `outer_bounds`를 직접 쓰지 않고, 같은 layer copper boxes 전체(terminal stub 포함 가능)의 planar bbox에서 파생되어야 한다.
- STEP export scene은 layer-aware body set을 내보내야 하며, TX multilayer면 `<pcb_prefix>_l{n}` bodies plus a single `tx_copper_stack` body를 내보낸다. fused copper body의 bbox는 terminal stub와 bus 하단까지 포함해야 한다.
- notebook-scale RX single-layer geometry에서도 scene copper fuse는 반드시 single solid여야 한다.
- metadata의 modeled object entry는 `object_id`, `role`, `material`, `model_state`, `step_path`, expected body names/count, canonical coordinates, terminal metadata를 빠짐없이 기록해야 한다.
- metadata의 modeled object entry는 `plane`, `placement_owner_id`, `start_point_plane_mm`, `end_point_plane_mm`까지 같이 기록해야 한다.
- direct export default는 zero placement offset이지만, type2 owner가 explicit placement offset을 주면 metadata는 local contract 대신 scene-absolute contract를 기록해야 한다.
- `build123d.export_step()`이 `True`를 반환하지 않으면 즉시 예외를 발생시킨다.
- profile-aware extrusion은 `XY` / `YZ` 모두에서 coil normal 방향 thickness를 실제 solid로 만들어야 한다.
- current implementation supports TX multilayer parallel-bus geometry/export, but RX는 shared engine/profile path를 쓰면서도 `layer_count != 1`이면 즉시 실패한다.

## 직접 의존
- 표준 라이브러리: `hashlib`, `json`, `math`, `tomllib`, `dataclasses`, `pathlib`
- 외부 라이브러리: `build123d`
- 내부 geometry helper: [[sdd/code/src/peetsfea/tx_rect_void_geometry.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/entry/export_tx_rect_void_step.py]]
- [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py]]

## 관련 테스트
- [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py]]

## TODO
- [ ] [[sdd/plans/0.2.22-type2-multilayer-tx-generic-single-coil]]를 따라 entry/import/notebook까지 generalized single-coil 계약을 전파한다.
- [ ] private sharp seed helper naming을 blunt/export contract와 혼동되지 않게 정리한다.
- [ ] file path와 public loader/export 함수 naming까지 role-neutral single-coil naming으로 정리하는 후속 리팩터링을 기록한다.
- [ ] TX/RX가 같은 geometry authoring engine과 profile injection path를 공유한다는 계약을 invariants 쪽에 더 직접적으로 적는다.
- [ ] role/profile만 다르고 engine은 같은지 검증하는 TX/RX 대칭 regression test 추가 작업을 기록한다.
- [ ] parser/schema/public docs에서 explicit `terminal_stub_length_mm` compatibility field를 제거하는 작업을 기록한다.

## 변경 시 주의점
- geometry recurrence의 핵심 hazard는 “centerline shaping helper”, “segment join authoring”, “debug boxes” 셋을 같은 owner처럼 다루는 것이다. joined segment primitive만 live geometry owner로 유지해야 한다.
- TOML schema 변경 시 [[docs/tx-rect-void-step]]와 [[sdd/plans/tx-rect-void-step-generator]]를 같이 갱신한다.
- STEP artifact를 tracked 파일로 추가하면 viewer registry 정책을 별도 계획으로 갱신해야 한다.
- 기본 generated STEP path나 generator entrypoint가 바뀌면 `notebooks/view_step_files.ipynb`의 tx_rect_void viewer cell도 같이 갱신한다.
- `modeled_objects` field naming이나 canonical coordinate semantics를 바꾸면 관련 테스트와 plan note를 같이 갱신한다.
- placement profile을 바꾸면 `tx_single_coil`의 XY owner 배치뿐 아니라 `rx_single_coil`의 YZ owner fit 조건과 terminal plane metadata도 같이 검증해야 한다.
- 기존 PyAEDT pipeline에 연결하려면 새 계획을 만들고 type dispatch, terminal, port, import 계약을 별도로 설계한다.
