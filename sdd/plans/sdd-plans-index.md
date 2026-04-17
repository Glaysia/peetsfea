---
title: Plan Note Index
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 20:25
tags:
  - sdd
---

# Plan Note Index

큰 변경, 장기 작업, 큰 리팩터링은 여기서 시작한다. 상위 허브는 [[sdd/sdd-index]], 템플릿은 [[sdd/templates/plan-note]]를 본다.

## Canonical Umbrella Plans
- [[sdd/plans/0.2.22-sdd-adoption]]
- [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]
- [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]]

## 현재 계획 문서
- `sdd/plans/0.2.22-sdd-adoption.md`
- `sdd/plans/0.2.22-src-entry-800-line-refactor-threshold.md`
- `sdd/plans/0.2.22-step-viewer-notebook-registry.md`
- `sdd/plans/0.2.22-type2-single-step-setup-ready-pipeline.md`
- `sdd/plans/0.2.22-type2-step-to-em-validate-pipeline.md`
- `sdd/plans/0.2.22-type2-toml-unification.md`
- `sdd/plans/0.2.22-type2-build123d-non-model-step.md`
- `sdd/plans/0.2.22-type2-pyaedt-step-import.md`
- `sdd/plans/0.2.22-type2-import-ledger-pipeline.md`
- `sdd/plans/0.2.22-type2-rx-single-coil.md`
- `sdd/plans/0.2.22-type2-multilayer-tx-generic-single-coil.md`
- `sdd/plans/0.2.22-type2-tx-underlay-mull12060ferrite.md`
- `sdd/plans/0.2.22-type2-single-coil-corner-relief.md`
- `sdd/plans/0.2.22-type2-tx-coil-geometry-repair.md`
- `sdd/plans/tx-rect-void-step-generator.md`

## Type2 milestone order
- single STEP + setup-ready notebook 방향: `sdd/plans/0.2.22-type2-single-step-setup-ready-pipeline.md`
- 상위 방향: `sdd/plans/0.2.22-type2-step-to-em-validate-pipeline.md`
- 완료 baseline: `sdd/plans/0.2.22-type2-build123d-non-model-step.md`
- 단일 SSOT 전환: `sdd/plans/0.2.22-type2-toml-unification.md`
- historical import smoke: `sdd/plans/0.2.22-type2-pyaedt-step-import.md`
- 구현된 import+ledger path: `sdd/plans/0.2.22-type2-import-ledger-pipeline.md`
- RX single-coil role 확장: `sdd/plans/0.2.22-type2-rx-single-coil.md`
- generalized engine + TX multilayer direction: `sdd/plans/0.2.22-type2-multilayer-tx-generic-single-coil.md`
- TX underlay tri-layer contract: `sdd/plans/0.2.22-type2-tx-underlay-mull12060ferrite.md`
- single-coil corner relief gap: `sdd/plans/0.2.22-type2-single-coil-corner-relief.md`
- TX coil geometry repair: `sdd/plans/0.2.22-type2-tx-coil-geometry-repair.md`
- 첫 modeled object role: `sdd/plans/tx-rect-void-step-generator.md`

## 규칙
- 신규 기능과 큰 리팩터링은 코드 전에, 또는 코드와 함께 계획 문서를 만든다.
- `src/` / `entry/`의 oversized tracked Python 파일 분리 기준은 `sdd/plans/0.2.22-src-entry-800-line-refactor-threshold.md`를 따른다.
- 계획 문서는 실제 영향 받는 코드 노트와 직접 선행/후속 계획으로 링크한다.
- 구현이 끝나면 상태, 결정, 남은 작업을 갱신한다.
