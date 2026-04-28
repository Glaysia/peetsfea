---
title: Plan Note Index
created: 2026-04-17 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - sdd
---

# Plan Note Index

큰 변경, 장기 작업, 큰 리팩터링은 여기서 시작한다. 상위 허브는 [sdd-index](../sdd-index.md), 템플릿은 [plan-note](../templates/plan-note.md)를 본다.

## Canonical Umbrella Plans
- [0.2.22-sdd-adoption](0.2.22-sdd-adoption.md)
- [0.2.22-src-entry-800-line-refactor-threshold](0.2.22-src-entry-800-line-refactor-threshold.md)
- [0.2.22-type2-step-to-em-validate-pipeline](0.2.22-type2-step-to-em-validate-pipeline.md)

## Active Type2 Plans
- `sdd/plans/0.2.24-type2-rxonly-tx-removal.md`
- `sdd/plans/0.2.22-type2-step-to-em-validate-pipeline.md`
- `sdd/plans/0.2.22-type2-rx-only-baseline.md`
- `sdd/plans/0.2.22-type2-rx-single-coil.md`
- `sdd/plans/0.2.22-type2-rx-single-coil-full-backing.md`
- `sdd/plans/0.2.22-type2-rx-plate-stack.md`
- `sdd/plans/0.2.22-type2-rx-plate-stack-striped-copper.md`
- `sdd/plans/0.2.22-type2-sampled-build-split.md`
- `sdd/plans/0.2.22-type2-import-ledger-pipeline.md`
- `sdd/plans/0.2.22-type2-step-spec-split.md`
- `sdd/plans/0.2.22-type2-toml-unification.md`
- `sdd/plans/0.2.22-type2-build123d-non-model-step.md`

## 0.2.24 Reset Note
- TX shape-specifying SDD has been pruned.
- RX plans remain active.
- `tx_region` remains only as future placement guide.
- Reusable EM output variable names are tracked in [type2-em-report-contract](../architecture/type2-em-report-contract.md).
- Implementation handoff for sub-agents is [0.2.24-type2-rxonly-tx-removal](0.2.24-type2-rxonly-tx-removal.md).

## 규칙
- 신규 기능과 큰 리팩터링은 코드 전에, 또는 코드와 함께 계획 문서를 만든다.
- 계획 문서는 실제 영향 받는 코드 노트와 직접 선행/후속 계획으로 링크한다.
