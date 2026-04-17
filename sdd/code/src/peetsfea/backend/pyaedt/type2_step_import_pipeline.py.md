---
title: type2_step_import_pipeline.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 17:20
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
- 현재 구현 기준으로 Type2 STEP import runtime의 orchestration facade다.
- 현재 구현 기준으로 STEP ledger load/validation, ownership partition, style/material/placement 검증 로직은 split module로 위임한다.
- 현재 구현 기준으로 facade는 HFSS session lifecycle, single scene import, imported ownership partition, runtime-owned post-import mesh assignment, boundary creation, imported ledger write, save/release 순서를 고정한다.
- 현재 구현 기준으로 type2 STEP ledger가 보존한 retained boundary policy(`type2_step_ledger.em_policy`)를 읽고, 새 type2 전용 helper를 정의하지 않은 채 기존 type1-style region/radiation helper contract를 재사용해 setup-ready boundary state를 만든다.
- 현재 구현 기준으로 imported ledger top-level metadata에 boundary summary를 결합한다.
- current single-coil exact-name contract adds the two sheet bodies `tx_port_sheet`, `rx_port_sheet`; later port-assignment adapter work is expected to consume them as reference surfaces.

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
- 현재 구현 기준으로 facade는 split module의 validated 결과를 결합해 imported object names와 boundary summary를 포함한 imported ledger payload를 만든다.
- boundary summary의 canonical source는 import 시점 HFSS live state가 아니라, type2 ledger retained boundary policy(`em_policy`)와 그 policy를 실행한 boundary helper 결과여야 한다.
- current single-coil mesh payload의 canonical source는 import runtime-owned exact contract다: `MeshSetup.AssignLengthOp(...)` named `Length1`, objects `["tx_copper_l0", "rx_copper_l0"]`, `RefineInside=False`, `Enabled=True`, `RestrictElem=False`, `NumMaxElem="1000"`, `RestrictLength=True`, `MaxLength="5mm"`다.
- imported modeled-object ownership also preserves exact-name participation of `tx_port_sheet` / `rx_port_sheet`; this does not mean the runtime already assigns lumped ports from those sheets.

## Invariants / fail-fast
- STEP ledger와 top-level `scene_step_path`는 HFSS launch 전에 검증된다.
- scene STEP import는 정확히 한 번 수행되고 import diff는 non-empty/duplicate-free여야 한다.
- imported ownership partition은 exact-name metadata 기준으로 수행된다.
- runtime-owned post-import mesh assignment는 imported modeled ledger entries가 이미 조립한 canonical `imported_object_names`만 읽는다. downstream geometry나 live object graph에서 mesh 대상을 역추론하지 않는다.
- `import_3d_cad`, `AssignLengthOp`, `save_project`, `release_desktop`의 `False` return은 즉시 raise한다.
- headless path는 release `close_projects=True, close_on_exit=True`, attached-session path는 detach release `False, False`를 유지한다.
- `MeshSetup` module lookup failure, missing object names `tx_copper_l0`/`rx_copper_l0`, `AssignLengthOp`의 `False` return은 즉시 raise 대상이다.
- type2 policy-owned `radiation_margin_mm`를 STEP ledger top-level `em_policy`에서 읽어 absolute-offset region 생성, exact 6-face 확인, face별 radiation assignment, boundary summary 기록을 수행한다.
- `create_region`, `get_object_faces`, `assign_radiation_boundary_to_faces`의 `False` return과 malformed face result도 즉시 raise 대상이다.
- exact-name import contract must distinguish PCB/copper styling ownership from port-sheet presence; port sheets are not implicitly copper or FR4 unless a later implementation says so explicitly.

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
- post-import mesh target selection은 imported modeled ledger entries가 확정한 exact imported names를 canonical source로 유지한다.
- boundary 동작은 type2 전용 helper를 새로 정의하는 방식이 아니라, 기존 type1 boundary helper contract를 import facade에서 재사용하는 방향을 유지한다.
- canonical docs는 retained policy key를 `em_policy`로 고정한다. 현재 runtime이 `import_time_policy`를 기대해 `notebooks/view_type2_hfss_import.ipynb` 실패를 노출하는 mismatch는 후속 코드 수정 대상이다.
- future port-sheet 문서화는 current import+ledger/boundary implementation 범위와 분리해 서술해야 하며, Python runtime 변경 전에는 sheet-based lumped-port assignment가 이미 landed 했다는 식으로 note를 쓰지 않는다.
