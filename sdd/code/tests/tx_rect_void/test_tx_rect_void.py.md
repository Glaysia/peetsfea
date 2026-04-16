# test_tx_rect_void.py

## Source
- Path: `tests/tx_rect_void/test_tx_rect_void.py`
- Code note path: `sdd/code/tests/tx_rect_void/test_tx_rect_void.py.md`
- Related plan: [[sdd/plans/tx-rect-void-step-generator]]
- Related code: [[sdd/code/src/peetsfea/tx_rect_void.py]]

## 역할
- Type2 rect/void STEP generator의 parser, deterministic realization, geometry, single-layer, fused-body export 계약을 pure-Python pytest로 검증한다.
- AEDT/HFSS launch 없이 build123d STEP export smoke만 수행한다.
- metadata JSON이 registry-aligned `modeled_objects` entry와 expected exported body contract를 포함하는지와 type2 TOML CLI smoke를 함께 검증한다.

## 입력 / 출력
- 입력: test-local TOML strings written under pytest `tmp_path`.
- 출력: pytest assertions, temporary STEP and metadata JSON files.

## Canonical state
- module-level runtime state는 없다.
- canonical fixtures는 `_spec_text()`가 생성하는 internal TX rect/void TOML이다.

## Invariants / fail-fast
- missing keys, bad ranges, unsupported terminal path, layer gap below 2mm는 즉시 실패해야 한다.
- supported corner/direction terminal paths는 axis-aligned route를 만들고 copper/void overlap을 만들면 안 된다.
- same-corner terminal path는 type1-derived planner를 사용해 outer terminal을 next-ring 좌표로 seed해야 한다.
- segment boxes는 centerline endpoint가 아니라 corner vertices까지 half-trace 연장되어야 한다.
- `layer_count=2` 또는 `3`은 via/layer contract가 없으므로 즉시 실패해야 한다.
- STEP scene은 debug copper segment가 여러 개여도 exported body로는 `tx_pcb_l0`, `tx_copper_l0` 두 solid만 가져야 한다.
- non-adjacent copper boxes가 겹치면 turn-to-turn short로 즉시 실패해야 한다.
- export smoke는 non-empty STEP과 metadata JSON을 생성해야 한다.
- metadata JSON은 single modeled object entry의 identity, role, model_state, expected body names/count, canonical coordinates, terminal metadata를 포함해야 한다.

## 직접 의존
- `pytest`
- [[sdd/code/src/peetsfea/tx_rect_void.py]]

## 이 파일을 쓰는 곳
- default pytest collection for the new standalone STEP workflow.

## 관련 테스트
- 이 파일 자체.

## 변경 시 주의점
- TOML schema나 geometry semantics를 바꾸면 fixture builder와 expected failure messages를 같이 갱신한다.
- Real AEDT import test를 이 파일에 넣지 않는다.
