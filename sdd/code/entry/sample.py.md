# entry/sample.py

- Source path: `entry/sample.py`
- Code note path: `[[sdd/code/entry/sample.py]]`
- Related policy: [[SDD]]
- Related hubs: [[sdd/index]], [[sdd/code/index]]
- Related plan: [[sdd/plans/0.2.22-sdd-adoption]]
- Related architecture: [[sdd/architecture/current-pipeline-sdd-view]]
- Related diagram: [[sdd/diagrams/sample-build-flow]]

## 역할
- batch profile 계산, feasible seed selection 호출, sample artifact generation, `manifest.json` 기록까지 샘플링 entry 흐름을 묶는다.
- `run/type1.toml` 기반의 대량 TOML 생성 작업에서 기본 실행 파라미터와 batch 단위를 정의한다.

## 입력 / 출력
- `iter_sample_batch_profiles(...) -> tuple[SampleBatchProfile, ...]`
- `generate_sample_manifest(...) -> list[SampleManifestEntry]`
- `generate_all_sample_manifests(...) -> list[list[SampleManifestEntry]]`
- `main() -> list[list[SampleManifestEntry]]`

## Canonical state
- module constants가 기본 sampling contract를 이룬다.
- canonical batch identity는 `seed_start`, `seed_end`, `target_count`를 가진 `SampleBatchProfile`이다.
- output canonical path는 `run/toml/toml_<version>_<seed_start>/manifest.json` 규칙을 따른다.

## Invariants / fail-fast
- batch count, seed span, total count는 양수여야 한다.
- sample entry 생성은 `generate_sample_artifact_for_seed()`의 fail-fast 계약을 그대로 따른다.
- manifest write는 생성된 entry들을 기준으로 단일 경로에 기록한다.
- default 동작은 headless sampling 흐름이며 fallback batch path를 두지 않는다.

## 직접 의존
- `peetsfea.pipeline.run_batch`
- `peetsfea.pipeline.selection.uniform_seedset`
- `peetsfea.console_log`
- `peetsfea.version`
- `concurrent.futures.ProcessPoolExecutor`

## 이 파일을 직접 쓰는 곳
- `entry/build.py`
- `tests/pipeline_runs/_run_script_artifacts_support.py`
- VS Code debug/task flow from `run/`

## 관련 테스트
- `tests/pipeline_runs/test_run_script_sample_artifacts.py`
- `tests/pipeline_runs/test_entrypoint_configs.py`
- `tests/pipeline_runs/test_manifest_determinism.py`
- [[sdd/code/tests/spec_resolver/test_sampling_registry.py]]

## 변경 시 주의점
- batch profile 규칙이 바뀌면 build replay와 manifest path 계산도 같이 확인해야 한다.
- sampling contract를 바꾸면 [[docs/current-pipeline]]와 [[sdd/diagrams/sample-build-flow]]를 같이 갱신한다.
- parallel/default worker semantics를 바꾸면 headless debug flow와 테스트 harness가 같이 영향받는다.
