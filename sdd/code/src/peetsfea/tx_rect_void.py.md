# tx_rect_void.py

## Source
- Path: `src/peetsfea/tx_rect_void.py`
- Code note path: `sdd/code/src/peetsfea/tx_rect_void.py.md`
- Related plan: [[sdd/plans/tx-rect-void-step-generator]]
- Related docs: [[docs/tx-rect-void-step]]

## 역할
- Standalone TX rectangular/void coil TOML을 읽고, deterministic sampled realization과 build123d STEP export를 수행한다.
- 기존 type1 PyAEDT/HFSS resolver와 분리된 STEP authoring path만 담당한다.
- metadata JSON에는 기존 `realized`/`boxes`와 함께 future type2 modeled-object ledger의 proto-contract가 되는 `modeled_objects`를 기록한다.

## 입력 / 출력
- 입력: `TxRectVoidSpec` TOML file, integer `seed`, output STEP path, metadata JSON path.
- 출력: `TxRectVoidExportResult`, STEP file, metadata JSON.
- 핵심 함수: `load_tx_rect_void_spec()`, `realize_tx_rect_void_spec()`, `build_tx_rect_void_box_specs()`, `export_tx_rect_void_step()`.

## Canonical state
- module-level mutable state는 없다.
- Canonical runtime state는 `RealizedTxRectVoidCoil` dataclass와 generated `BoxSpec` tuple이다.
- export canonical metadata에는 single-entry `modeled_objects`와 그 안의 canonical coordinates, terminal metadata가 포함된다.
- Sampling owner identity는 TOML path string plus seed hash로 결정된다.

## Invariants / fail-fast
- `design.units`는 `mm`이어야 한다.
- range table은 `[is_integer, start, end, count]` 형식이어야 하며, count는 1 이상이어야 한다.
- `turn_count`는 1..9, `layer_count`는 1..3, `layer_gap_mm`는 2.0 이상이어야 한다.
- void bounds는 outer bounds 안에 axis-specific margin을 두고 들어와야 한다.
- generated copper box는 void keepout과 면적으로 겹치면 즉시 예외를 발생시킨다.
- metadata의 modeled object entry는 `object_id`, `role`, `material`, `model_state`, `step_path`, canonical coordinates, terminal metadata를 빠짐없이 기록해야 한다.
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
- `modeled_objects` field naming이나 canonical coordinate semantics를 바꾸면 관련 테스트와 plan note를 같이 갱신한다.
- 기존 PyAEDT pipeline에 연결하려면 새 계획을 만들고 type dispatch, terminal, port, import 계약을 별도로 설계한다.
