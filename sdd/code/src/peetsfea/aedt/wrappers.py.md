---
title: wrappers.py
created: 2026-04-17 @ 09:09
updated: 2026-04-22 @ 04:55
tags:
  - aedt
---

# wrappers.py

## Source
- Path: `src/peetsfea/aedt/wrappers.py`
- Code note path: `sdd/code/src/peetsfea/aedt/wrappers.py.md`
- Related plan: [[sdd/plans/0.2.22-type2-pyaedt-step-import]]
- Related umbrella plan: [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]]
- Related type2 architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- Raw PyAEDT `Hfss`, `Modeler3D`, `Object3d` boundary를 repository fail-fast wrapper로 감싼다.
- PyAEDT method access를 allowlist로 제한하고 false-return API를 즉시 예외로 변환한다.

## 입력 / 출력
- `Hfss(...)` wrapper constructor and exposed properties/methods
- `Modeler3D.object_names -> list[str]`
- `Modeler3D.import_3d_cad(...) -> bool`
- `Object3d` safe property/method facade

## Canonical state
- 각 wrapper instance의 canonical state는 `_raw` PyAEDT object reference다.
- imported object discovery는 raw `Modeler3D.object_names`를 validated list로 노출한다.
- HFSS validation settings are exposed through an allowlisted `change_validation_settings()` wrapper with explicit
  entity-check-level validation and false-return fail-fast behavior.

## Invariants / fail-fast
- raw attribute/method가 없거나 callable shape가 아니면 `assert`로 즉시 멈춘다.
- PyAEDT call result가 `False`이면 `raise_on_false()`가 operation/context와 함께 raise한다.
- `object_names`는 sequence of non-empty `str`이어야 하며 AEDT name length를 만족해야 한다.
- `import_3d_cad()`는 PyAEDT `0.25.1` 지원 인자만 전달하고 newer stable-doc 인자 fallback을 추가하지 않는다.
- `change_validation_settings()` accepts only PyAEDT-supported entity check levels and propagates `ignore_unclassified`
  / `skip_intersections` exactly.

## 직접 의존
- `ansys.aedt.core`
- `ansys.aedt.core.modeler`
- `peetsfea.aedt.failfast`

## 이 파일을 쓰는 곳
- `peetsfea.aedt` top-level exports
- backend geometry and EM pipeline code that imports `Hfss`, `Modeler3D`, `Object3d`
- [[sdd/code/entry/import_non_model_step_to_hfss.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_smoke.py]]
- `tests/backend_em/test_aedt_sidecar_modeler.py`
- `tests/backend_em/test_aedt_sidecar_session.py`

## 변경 시 주의점
- allowlist를 넓힐 때마다 fail-fast validation과 false-return handling을 같이 추가한다.
- PyAEDT version/API drift가 있으면 wrapper signature, protocol, tests, related SDD plan을 같이 갱신한다.
- raw object method를 fallback으로 직접 노출하면 `CODE_COMMANDMENTS.md`의 boundary fail-fast 의도를 약화시킬 수 있다.
