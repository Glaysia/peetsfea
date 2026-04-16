# tx_rect_void.py

## Source
- Path: `src/peetsfea/tx_rect_void.py`
- Code note path: `sdd/code/src/peetsfea/tx_rect_void.py.md`
- Related plan: [[sdd/plans/tx-rect-void-step-generator]]
- Related docs: [[docs/tx-rect-void-step]]
- Related STEP viewer registry: [[sdd/plans/0.2.22-step-viewer-notebook-registry]]

## 역할
- Type2 modeled `tx_single_coil` rect/void spec을 읽고, deterministic sampled realization과 build123d STEP export를 수행한다.
- 기존 type1 PyAEDT/HFSS resolver와 분리된 STEP authoring path만 담당한다.
- metadata JSON에는 `realized`/debug `boxes`, fused STEP body expectation, type2 modeled-object ledger가 되는 `modeled_objects`를 기록한다.
- Type1 neo TX DD에서 해결한 same-corner terminal planner와 outer terminal seed 규칙을 type2 STEP 경로에 적용한다.

## 입력 / 출력
- 입력: `TxRectVoidSpec`, source TOML path, integer `seed`, output STEP path, metadata JSON path.
- 출력: `TxRectVoidExportResult`, STEP file, metadata JSON.
- 핵심 함수: `load_tx_rect_void_spec()`, `realize_tx_rect_void_spec()`, `build_tx_rect_void_box_specs()`, `build_tx_rect_void_step_scene()`, `export_tx_rect_void_step_from_spec()`.

## Canonical state
- module-level mutable state는 없다.
- Canonical runtime state는 `RealizedTxRectVoidCoil` dataclass와 generated `BoxSpec` tuple이다.
- export canonical metadata에는 single-entry `modeled_objects`, expected exported body names/count, canonical coordinates, terminal metadata가 포함된다.
- Sampling owner identity는 TOML path string plus seed hash로 결정된다.
- Centerline canonical state는 type1-derived same-corner path planner가 만든 point sequence다. `boxes`는 이 centerline에서 파생된 debug decomposition이다.

## Invariants / fail-fast
- `design.units`는 `mm`이어야 한다.
- range table은 `[is_integer, start, end, count]` 형식이어야 하며, count는 1 이상이어야 한다.
- `outer_y_mm`는 ratio가 아니라 canonical mm 단위 range다.
- `turn_count`는 1..4, `layer_count`는 반드시 1, `layer_gap_mm`는 2.0 이상이어야 한다.
- `metal_fill_factor`는 0.15..0.60이어야 하며 realized trace width는 모든 side에서 0.5mm 이상이어야 한다.
- v1은 centered same-corner route만 지원하므로 void center ratios는 public type2 example에서 0으로 고정한다.
- void bounds는 outer bounds 안에 axis-specific margin을 두고 들어와야 한다.
- generated copper box는 void keepout과 면적으로 겹치면 즉시 예외를 발생시킨다.
- non-adjacent generated copper boxes가 겹치면 turn-to-turn short로 간주하고 즉시 예외를 발생시킨다.
- outer terminal point는 type1 neo TX DD처럼 next-ring coordinate로 seed되어야 하며, outer rectangle corner에 직접 남아 있으면 안 된다.
- segment box는 centerline endpoint에서 끊기지 않고 진행 방향으로 half-trace만큼 양끝을 연장해 corner-cap을 만든다. 이 규칙이 trace 꼭짓점끼리의 접합을 보장한다.
- STEP export scene은 `tx_pcb_l0`, fused `tx_copper_l0` 두 body만 내보내야 하며 copper fuse 결과가 단일 solid가 아니면 즉시 예외를 발생시킨다.
- metadata의 modeled object entry는 `object_id`, `role`, `material`, `model_state`, `step_path`, expected body names/count, canonical coordinates, terminal metadata를 빠짐없이 기록해야 한다.
- `build123d.export_step()`이 `True`를 반환하지 않으면 즉시 예외를 발생시킨다.

## 직접 의존
- 표준 라이브러리: `hashlib`, `json`, `math`, `tomllib`, `dataclasses`, `pathlib`
- 외부 라이브러리: `build123d`

## 이 파일을 쓰는 곳
- [[sdd/code/entry/export_tx_rect_void_step.py]]
- [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py]]

## 관련 테스트
- [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py]]

## 변경 시 주의점
- TOML schema 변경 시 [[docs/tx-rect-void-step]]와 [[sdd/plans/tx-rect-void-step-generator]]를 같이 갱신한다.
- STEP artifact를 tracked 파일로 추가하면 viewer registry 정책을 별도 계획으로 갱신해야 한다.
- 기본 generated STEP path나 generator entrypoint가 바뀌면 `notebooks/view_step_files.ipynb`의 tx_rect_void viewer cell도 같이 갱신한다.
- `modeled_objects` field naming이나 canonical coordinate semantics를 바꾸면 관련 테스트와 plan note를 같이 갱신한다.
- 기존 PyAEDT pipeline에 연결하려면 새 계획을 만들고 type dispatch, terminal, port, import 계약을 별도로 설계한다.
