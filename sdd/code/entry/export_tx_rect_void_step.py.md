---
title: export_tx_rect_void_step.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - tx-rect-void
  - step-export
---

# export_tx_rect_void_step.py

## Source
- Path: `entry/export_tx_rect_void_step.py`
- Code note path: `sdd/code/entry/export_tx_rect_void_step.py.md`
- Related plan: [[sdd/plans/tx-rect-void-step-generator]]
- Related docs: [[docs/tx-rect-void-step]]
- Related STEP viewer registry: [[sdd/plans/0.2.22-step-viewer-notebook-registry]]

## 역할
- `examples/type2_fixed.toml`의 modeled `tx_single_coil` object를 STEP으로 export하는 얇은 CLI entrypoint다.
- CLI argument parsing과 default path wiring만 담당하고, type2 parsing/export orchestration은 [[sdd/code/entry/generate_type2_step.py]]에 위임한다.
- 출력 metadata JSON은 기존 export payload에 더해 registry-aligned `modeled_objects` proto-contract를 함께 기록한다.

## 입력 / 출력
- 입력: `--toml`, `--output-step`, `--metadata`, `--seed`.
- 기본 입력: `examples/type2_fixed.toml`.
- 기본 출력: `run/step/tx_rect_void_coil.step`, `run/step/tx_rect_void_coil.metadata.json`.
- viewer notebook: `notebooks/view_step_files.ipynb`의 generated STEP viewer cell.

## Canonical state
- module-level mutable state는 없다.
- 기본 path constants는 CLI default contract다.

## Invariants / fail-fast
- type2 parser와 `tx_rect_void` geometry/export failure를 즉시 예외로 전달한다.
- 이 entrypoint는 AEDT/HFSS를 launch하지 않는다.

## 직접 의존
- `argparse`
- `pathlib.Path`
- [[sdd/code/entry/generate_type2_step.py]]

## 이 파일을 쓰는 곳
- 사람이 직접 실행하는 type2 single-coil direct STEP export CLI.
- [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py]]는 CLI smoke로 이 entrypoint를 검증한다.

## 관련 테스트
- [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py]]
- CLI smoke: `.venv/bin/python entry/export_tx_rect_void_step.py --seed 0`

## 변경 시 주의점
- 기본 output path를 바꾸면 [[docs/tx-rect-void-step]]와 [[sdd/plans/tx-rect-void-step-generator]]도 갱신한다.
- 기본 STEP output path나 metadata path를 바꾸면 `notebooks/view_step_files.ipynb`의 generated viewer cell도 같이 갱신한다.
- metadata JSON shape를 바꾸면 CLI smoke expectation과 [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py]]를 같이 갱신한다.
- 이 entrypoint에 AEDT import를 섞지 않는다. import는 별도 계획이 필요하다.
