# tests/spec_resolver/test_sampling_registry.py

- Source path: `tests/spec_resolver/test_sampling_registry.py`
- Code note path: `[[sdd/code/tests/spec_resolver/test_sampling_registry.py]]`
- Related policy: [[SDD]]
- Related hubs: [[sdd/index]], [[sdd/code/index]]
- Related plan: [[sdd/plans/0.2.22-sdd-adoption]]
- Related architecture: [[sdd/architecture/current-pipeline-sdd-view]]
- Related diagram: [[sdd/diagrams/sample-build-flow]]

## 역할
- sampling registry의 coverage, unknown field preflight, duplicate owner rejection, normalized-away field 고정 규칙을 회귀 테스트로 고정한다.
- selection 단계가 fail-fast 계약을 잃지 않도록 최소 방어선을 제공한다.

## 입력 / 출력
- pytest가 수집하는 test module이다.
- `write_type1_toml()`로 fixture spec을 만들고 `load_toml_bytes()`와 `resolve_selection()`을 호출한다.
- 성공 시 아무 값도 반환하지 않고, 계약 위반 시 기대한 예외를 검증한다.

## Canonical state
- module-level runtime state는 없다.
- canonical test fixture는 `tests/fixtures/type1_spec.py`가 생성하는 type1 TOML이다.

## Invariants / fail-fast
- scanned sample-like field set은 registry known path set과 정확히 같아야 한다.
- unknown sampled field는 preflight에서 `ValueError`로 즉시 실패해야 한다.
- duplicate sampling owner registration은 허용되지 않는다.
- normalized-away sampled field는 `count=1`로 고정되지 않으면 실패해야 한다.

## 직접 의존
- `pytest`
- [[sdd/code/src/peetsfea/spec/loader.py]]
- `peetsfea.spec.resolver`
- `peetsfea.spec.resolver.sampling`
- `tests.fixtures.type1_spec`

## 이 파일을 쓰는 곳
- `pytest` test collection
- sampling registry 변경 작업의 회귀 기준

## 관련 테스트
- 이 파일 자체
- `tests/spec_resolver/test_selection_result.py`
- `tests/pipeline_runs/test_manifest_constraints.py`
- `tests/pipeline_outputs/test_uniform_seedset.py`

## 변경 시 주의점
- sampling registry path naming을 바꾸면 expected error message와 coverage assertion을 같이 갱신해야 한다.
- fail-fast 정책을 약화하면 [[CODE_COMMANDMENTS]]와 충돌한다.
- selection contract가 바뀌면 [[sdd/architecture/current-pipeline-sdd-view]]와 관련 코드 노트를 같이 갱신한다.
