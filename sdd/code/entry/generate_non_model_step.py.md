---
title: generate_non_model_step.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - step-export
---

# generate_non_model_step.py

## Source
- Path: `entry/generate_non_model_step.py`
- Code note path: `sdd/code/entry/generate_non_model_step.py.md`
- Related plan: [[sdd/plans/0.2.22-type2-build123d-non-model-step]]
- Related umbrella plan: [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]]
- Related STEP viewer registry: [[sdd/plans/0.2.22-step-viewer-notebook-registry]]
- Related type2 architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- unified type2 TOML의 `non_model_objects`를 읽어 build123d box compound를 생성하고 STEP artifact로 export한다.
- AEDT import 전 단계의 geometry authoring smoke path만 담당한다.
- 특정 object id에 분기하지 않고 TOML의 `non_model_objects` 배열을 그대로 검증/export한다.

## 입력 / 출력
- 입력: `examples/type2_fixed.toml`
- 출력: `run/step/type2/type2_non_model_scene.step`
- viewer registry: unified generated modeled artifact is registered; this non-model compound smoke output is no longer a tracked viewer artifact.
- CLI entry: `.venv/bin/python entry/generate_non_model_step.py`
- stdout: source TOML, output STEP, non-model object count, compound bounding box

## Canonical state
- 없음.
- canonical 입력은 unified type2 TOML의 `non_model_objects` 배열이고, 스크립트는 이를 매 실행마다 다시 읽는다.

## Invariants / fail-fast
- `non_model_objects`는 비어 있으면 안 된다.
- 각 object는 table이어야 하며 `id`, `kind`, `primitive`, `present`, `non_model`, `material`, `plane`, `origin_xyz`, `size_xyz`를 가져야 한다.
- `primitive`는 `box`만 허용한다.
- `present`와 `non_model`은 `true`만 허용한다.
- `plane`은 `XY`, `YZ`, `ZX` 중 하나여야 한다.
- `origin_xyz`와 `size_xyz`는 숫자 3개여야 하며, `size_xyz`는 모두 양수여야 한다.
- 중복 `id`와 `build123d.export_step()` 실패는 즉시 예외를 발생시킨다.

## 직접 의존
- Python 표준 라이브러리: `pathlib`, `tomllib`, `typing`
- 외부 라이브러리: `build123d`

## 이 파일을 쓰는 곳
- 현재는 직접 import하는 runtime code가 없다.
- 사람이 직접 실행하는 type2 STEP 생성 smoke script다.

## 관련 테스트
- 직접 자동 테스트는 아직 없다.
- 검증 명령:
  - `.venv/bin/python entry/generate_non_model_step.py`
  - `test -s run/step/type2/type2_non_model_scene.step`

## 변경 시 주의점
- TOML schema를 바꾸면 [[sdd/plans/0.2.22-type2-build123d-non-model-step]]도 같이 갱신한다.
- `origin_xyz` 해석을 바꾸면 기존 STEP artifact의 좌표계가 바뀐다.
- type2 TX 영역은 현재 단일 `tx_region` box로 기록하며, sub-zone을 되살리려면 TOML과 계획 노트를 먼저 갱신한다.
- tracked STEP artifact를 추가하면 `notebooks/view_step_files.ipynb`의 `STEP_ARTIFACTS` registry와 viewer cell을 같이 갱신한다.
- runtime parser에 연결하기 전까지 이 파일은 type2 실험용 smoke path로 유지한다.
