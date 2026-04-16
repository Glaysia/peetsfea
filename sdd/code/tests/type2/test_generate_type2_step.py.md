# test_generate_type2_step.py

## Source
- Path: `tests/type2/test_generate_type2_step.py`
- Code note path: `sdd/code/tests/type2/test_generate_type2_step.py.md`
- Related code: [[sdd/code/examples/type2/generate_type2_step.py]]
- Related plan: [[sdd/plans/0.2.22-type2-toml-unification]]

## 역할
- `generate_type2_step.py`의 type2.toml parser와 object-level STEP export 계약을 pure-Python pytest로 검증한다.
- type2 단일 SSOT(`examples/type2/type2.toml`) 경로가 동작하는지와 fail-fast 위반 케이스를 확인한다.

## 입력 / 출력
- 입력:
  - repository example `examples/type2/type2.toml`
  - test-local minimal type2 TOML fixtures
- 출력:
  - `tmp_path` 아래 generated STEP files and ledger JSON
  - pytest assertions only (no AEDT launch, no solve)

## Canonical state
- module-level mutable state는 없다.
- canonical fixture는 `_type2_spec_text()`가 만드는 minimal unified type2 TOML이다.

## Invariants / fail-fast
- example `type2.toml`은 7 non-model + 1 modeled object로 파싱되어야 한다.
- example `type2.toml`의 modeled object는 `outer_y_mm`, `turn_count=1..4`, `layer_count=1` 계약을 가져야 한다.
- duplicate object id는 즉시 실패해야 한다.
- unsupported modeled role은 즉시 실패해야 한다.
- modeled required field 누락(`terminal_path`)은 즉시 실패해야 한다.
- invalid terminal path는 modeled export 단계에서 즉시 실패해야 한다.
- non-model `build123d.export_step()`가 `False`면 즉시 실패해야 한다.
- 성공 케이스에서는 object-level STEP files와 ledger JSON이 모두 생성되고 modeled ledger에 expected exported body names/count가 기록되어야 한다.

## 직접 의존
- `pytest`
- [[sdd/code/examples/type2/generate_type2_step.py]]

## 이 파일을 쓰는 곳
- default pytest collection.

## 관련 테스트
- 이 파일 자체.

## 변경 시 주의점
- type2 TOML field 이름을 바꾸면 fixture text와 assertion field path를 함께 갱신한다.
- ledger shape를 바꾸면 이 테스트와 downstream import tests를 함께 갱신한다.
