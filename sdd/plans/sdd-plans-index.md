---
title: Plan Note Index
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - sdd
---

# Plan Note Index

큰 변경, 장기 작업, 큰 리팩터링은 여기서 시작한다. 상위 허브는 [[sdd/sdd-index]], 템플릿은 [[sdd/templates/plan-note]]를 본다.

## 현재 계획 문서
- [[sdd/plans/0.2.22-sdd-adoption]]
- [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]
- [[sdd/plans/0.2.22-step-viewer-notebook-registry]]
- [[sdd/plans/0.2.22-type2-single-step-setup-ready-pipeline]]
- [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]]
- [[sdd/plans/0.2.22-type2-toml-unification]]
- [[sdd/plans/0.2.22-type2-build123d-non-model-step]]
- [[sdd/plans/0.2.22-type2-pyaedt-step-import]]
- [[sdd/plans/0.2.22-type2-import-ledger-pipeline]]
- [[sdd/plans/0.2.22-type2-rx-single-coil]]
- [[sdd/plans/0.2.22-type2-multilayer-tx-generic-single-coil]]
- [[sdd/plans/0.2.22-type2-single-coil-corner-relief]]
- [[sdd/plans/0.2.22-type2-tx-coil-geometry-repair]]
- [[sdd/plans/tx-rect-void-step-generator]]

## Type2 milestone order
- single STEP + setup-ready notebook 방향: [[sdd/plans/0.2.22-type2-single-step-setup-ready-pipeline]]
- 상위 방향: [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]]
- 완료 baseline: [[sdd/plans/0.2.22-type2-build123d-non-model-step]]
- 단일 SSOT 전환: [[sdd/plans/0.2.22-type2-toml-unification]]
- historical import smoke: [[sdd/plans/0.2.22-type2-pyaedt-step-import]]
- 구현된 import+ledger path: [[sdd/plans/0.2.22-type2-import-ledger-pipeline]]
- RX single-coil role 확장: [[sdd/plans/0.2.22-type2-rx-single-coil]]
- generalized engine + TX multilayer direction: [[sdd/plans/0.2.22-type2-multilayer-tx-generic-single-coil]]
- single-coil corner relief gap: [[sdd/plans/0.2.22-type2-single-coil-corner-relief]]
- TX coil geometry repair: [[sdd/plans/0.2.22-type2-tx-coil-geometry-repair]]
- 첫 modeled object role: [[sdd/plans/tx-rect-void-step-generator]]

## 규칙
- 신규 기능과 큰 리팩터링은 코드 전에, 또는 코드와 함께 계획 문서를 만든다.
- `src/` / `entry/`의 oversized tracked Python 파일 분리 기준은 [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]를 따른다.
- 계획 문서는 실제 영향 받는 코드 노트와 직접 선행/후속 계획으로 링크한다.
- 구현이 끝나면 상태, 결정, 남은 작업을 갱신한다.
