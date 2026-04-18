---
title: test_type2_step_import_smoke.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - hfss-import
---

# test_type2_step_import_smoke.py

## Source
- Path: `tests/backend_em/test_type2_step_import_smoke.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_step_import_smoke.py.md`
- Related plan: [[sdd/plans/0.2.22-type2-pyaedt-step-import]]
- Related umbrella plan: [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]]
- Related type2 architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- Type2 STEP PyAEDT import smoke path를 AEDT launch 없이 fake sessions로 검증한다.
- `Modeler3D.import_3d_cad` wrapper의 false-return과 `object_names` shape validation을 방어한다.

## 입력 / 출력
- pytest tests under `tests/backend_em`
- fake raw modeler and fake HFSS session objects
- no AEDT process launch, no real `.aedt` solve artifact

## Canonical state
- test-local fake objects hold call ledgers for import, non-model state changes, save, release.
- canonical assertion target is the returned `Type2StepImportResult` and fake call history.

## Invariants / fail-fast
- `import_3d_cad(False)` must raise through `raise_on_false`.
- wrapper must reject invalid `object_names` raw shape.
- smoke script must set each newly imported object to `model=False`.
- smoke script must save and release the fake desktop exactly once.

## 직접 의존
- `pytest`
- `peetsfea.aedt.Modeler3D`
- `entry.import_non_model_step_to_hfss`

## 이 파일을 쓰는 곳
- default/test command path only.

## 관련 테스트
- This file is the direct test note target for [[sdd/code/entry/import_non_model_step_to_hfss.py]].

## 변경 시 주의점
- Adding real AEDT launch to this file would violate its pure-Python smoke-test role.
- If wrapper signature changes, keep fake modeler and Protocol expectations aligned.
