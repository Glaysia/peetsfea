# test_tx_rect_void.py

## Source
- Path: `tests/tx_rect_void/test_tx_rect_void.py`
- Code note path: `sdd/code/tests/tx_rect_void/test_tx_rect_void.py.md`
- Related plan: [[sdd/plans/tx-rect-void-step-generator]]
- Related code: [[sdd/code/src/peetsfea/tx_rect_void.py]]

## 역할
- Standalone TX rect/void STEP generator의 parser, deterministic realization, geometry, stack, export 계약을 pure-Python pytest로 검증한다.
- AEDT/HFSS launch 없이 build123d STEP export smoke만 수행한다.

## 입력 / 출력
- 입력: test-local TOML strings written under pytest `tmp_path`.
- 출력: pytest assertions, temporary STEP and metadata JSON files.

## Canonical state
- module-level runtime state는 없다.
- canonical fixtures는 `_spec_text()`가 생성하는 standalone TX rect/void TOML이다.

## Invariants / fail-fast
- missing keys, bad ranges, unsupported terminal path, layer gap below 2mm는 즉시 실패해야 한다.
- supported corner/direction terminal paths는 axis-aligned route를 만들고 copper/void overlap을 만들면 안 된다.
- `layer_count=3`은 PCB slab 3개와 expected z positions를 만든다.
- export smoke는 non-empty STEP과 metadata JSON을 생성해야 한다.

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

## Links
- [[SDD]]
- [[AGENTS]]
- [[CODE_COMMANDMENTS]]
- [[sdd/sdd-index]]
- [[sdd/code/sdd-code-index]]
