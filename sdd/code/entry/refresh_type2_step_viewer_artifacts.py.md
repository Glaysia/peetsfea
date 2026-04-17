---
title: refresh_type2_step_viewer_artifacts.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - type2
  - step-export
---

# refresh_type2_step_viewer_artifacts.py

## Source
- Path: `entry/refresh_type2_step_viewer_artifacts.py`
- Code note path: `sdd/code/entry/refresh_type2_step_viewer_artifacts.py.md`
- Related plan: [[sdd/plans/0.2.22-step-viewer-notebook-registry]]
- Related test: [[sdd/code/tests/type2/test_refresh_type2_step_viewer_artifacts.py]]

## 역할
- type2 STEP viewer notebook가 쓰는 generated artifact 집합을 clean refresh한다.
- `run/step/type2`를 삭제한 뒤 `examples/type2_fixed.toml` 기준으로 STEP artifacts와 ledger를 다시 생성한다.
- refresh 직후 ledger placement contract를 검증하고 canonical scene STEP path를 notebook consumer에 돌려준다.

## 입력 / 출력
- 입력:
  - `examples/type2_fixed.toml`
  - output dir (`run/step/type2`)
  - ledger path (`run/step/type2/type2_step_ledger.json`)
  - scene STEP expectation (`run/step/type2/type2_scene.step`)
  - `seed`
- 출력:
  - refreshed single scene STEP + metadata ledger
  - refreshed ledger JSON
  - `Type2StepViewerRefreshResult`

## Canonical state
- canonical generated source는 `type2_step_ledger.json`이다.
- notebook-visible generated artifact는 refresh가 끝난 뒤의 `type2_scene.step` 하나다.
- placement truth는 regenerated ledger의 canonical coordinates다.

## Invariants / fail-fast
- `run/step/type2`가 존재하면 디렉터리여야 하며 refresh 전에 통째로 삭제한다.
- export 후 ledger file이 반드시 다시 존재해야 한다.
- export 후 ledger top-level `scene_step_path`가 반드시 존재해야 한다.
- stale `type2_combined_preview.step`와 `objects/` 산출물은 refresh 후 남아 있으면 안 된다.
- TX는 `tx_region` 내부 centered X/Y + owner max-Z 접촉이어야 한다.
- RX는 `rx_region_actual` 내부 centered Y + owner min-Z 접촉 + owner max-X 접촉이어야 한다.
- placement contract mismatch, missing artifact, `build123d.export_step()` false는 즉시 raise한다.

## 직접 의존
- [[sdd/code/entry/generate_type2_step.py]]

## 이 파일을 쓰는 곳
- `notebooks/view_step_files.ipynb`
- 사람이 직접 실행하는 refresh CLI

## 관련 테스트
- [[sdd/code/tests/type2/test_refresh_type2_step_viewer_artifacts.py]]

## TODO
- [ ] viewer notebook가 ledger summary도 함께 보여줄지 결정한다.
- [ ] geometry team single-scene contract가 바뀌면 refresh result shape를 notebook과 함께 재고정한다.
- [ ] setup-ready import notebook slice와 공통 artifact manifest를 공유할지 정리한다.

## 변경 시 주의점
- notebook generated artifact contract를 바꾸면 이 entry와 notebook cell을 같이 갱신한다.
- canonical scene STEP 경로를 바꾸면 notebook과 테스트를 같이 갱신한다.
- placement validation은 geometry를 repair하지 않고 ledger mismatch를 즉시 드러내는 용도다.
