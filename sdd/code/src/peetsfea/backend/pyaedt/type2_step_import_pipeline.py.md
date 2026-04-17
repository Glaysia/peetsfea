---
title: type2_step_import_pipeline.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 10:41
tags:
  - type2
  - hfss-import
  - aedt
---

# type2_step_import_pipeline.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py.md`
- Related plan: [[sdd/plans/0.2.22-type2-import-ledger-pipeline]]
- Related architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]
- Collaborators:
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py]]
  - [[sdd/code/src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py]]

## 역할
- Type2 STEP import runtime의 orchestration facade다.
- STEP ledger load/validation, ownership partition, style/material/placement 검증 로직은 split module로 위임한다.
- facade는 HFSS session lifecycle, single scene import 호출, imported ledger write/save/release 순서를 고정한다.

## 입력 / 출력
- 입력:
  - `run/step/type2/type2_step_ledger.json`
  - HFSS session factory
- 추가 입력:
  - 이미 열린 `HfssSession` (`import_type2_step_ledger_into_hfss`)
- 출력:
  - `run/aedt/type2_step_import/type2_import.aedt`
  - `run/aedt/type2_step_import/type2_imported_ledger.json`
  - `Type2ImportedLedger`

## Canonical state
- Module-level mutable state는 없다.
- Canonical role/coordinate/terminal source는 export ledger다.
- Canonical artifact path는 export ledger top-level `scene_step_path`다.
- facade는 split module의 validated 결과를 결합해 최종 imported ledger payload를 만든다.

## Invariants / fail-fast
- STEP ledger와 top-level `scene_step_path`는 HFSS launch 전에 검증된다.
- scene STEP import는 정확히 한 번 수행되고 import diff는 non-empty/duplicate-free여야 한다.
- imported ownership partition은 exact-name metadata 기준으로 수행된다.
- `import_3d_cad`, `save_project`, `release_desktop`의 `False` return은 즉시 raise한다.
- headless path는 release `close_projects=True, close_on_exit=True`, attached-session path는 detach release `False, False`를 유지한다.

## 직접 의존
- `peetsfea.aedt.Hfss`
- `peetsfea.aedt.protocols`
- `peetsfea.aedt.failfast`
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_modeled_import_adapter.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/entry/import_type2_step.py]]
- `notebooks/view_type2_hfss_import.ipynb`
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]
- [[sdd/code/tests/type2/test_import_type2_step_entry.py]]

## 변경 시 주의점
- facade public API (`import_type2_step_ledger*`, defaults, `Type2ImportedLedger`)는 caller contract다.
- partition/style/ledger ownership을 facade로 재집중시키지 않는다.
- imported ledger schema 변경 시 CLI/tests/architecture/adapter 계획을 같이 갱신한다.
