---
title: protocols.py
created: 2026-04-17 @ 09:09
updated: 2026-04-22 @ 04:55
tags:
  - aedt
---

# protocols.py

## Source
- Path: `src/peetsfea/aedt/protocols.py`
- Code note path: `sdd/code/src/peetsfea/aedt/protocols.py.md`
- Related plan: [0.2.22-type2-step-to-em-validate-pipeline](../../../../plans/0.2.22-type2-step-to-em-validate-pipeline.md)
- Related umbrella plan: [0.2.22-type2-step-to-em-validate-pipeline](../../../../plans/0.2.22-type2-step-to-em-validate-pipeline.md)
- Related type2 architecture: [type2-step-to-em-validate-pipeline](../../../../architecture/type2-step-to-em-validate-pipeline.md)

## 역할
- AEDT/PyAEDT session boundary의 structural Protocol 타입을 정의한다.
- production wrapper와 pure-Python fake tests가 공유하는 최소 interface contract를 제공한다.
- current type2 setup-ready import work를 위해 mesh module lookup 이후 `AssignLengthOp(...)` boundary도 typed surface로 유지한다.

## 입력 / 출력
- `HfssSession`, `ModelerSession`, module/session Protocol classes
- `ModelerSession.object_names`
- `ModelerSession.import_3d_cad(...) -> bool`
- `ModelerSession.set_object_model_state(...) -> object`
- `MeshModuleSession.AssignLengthOp(...) -> object`
- `HfssSession.change_validation_settings(...) -> object`

## Canonical state
- module-level mutable state는 없다.
- canonical contract는 Protocol method/attribute signatures다.

## Invariants / fail-fast
- Protocol은 fallback behavior를 구현하지 않고 required boundary shape만 선언한다.
- `ModelerSession.import_3d_cad()` signature는 repo-pinned PyAEDT `0.25.1` wrapper와 일치해야 한다.
- `MeshModuleSession`은 `MeshSetup` lookup 이후 explicit cast target이며 `False` return fail-fast enforcement는 runtime layer가 담당한다.
- `change_validation_settings()` exposes PyAEDT's validation-design setting boundary; callers still fail fast on `False`.
- runtime validation은 [wrappers.py](wrappers.py.md)가 담당한다.

## 직접 의존
- `collections.abc.Mapping`, `collections.abc.Sequence`
- `pathlib.Path`
- `typing.Protocol`

## 이 파일을 쓰는 곳
- `peetsfea.aedt.proxies`
- backend tests with fake AEDT sessions
- [test_type2_step_import_smoke.py](../../../tests/backend_em/test_type2_step_import_smoke.py.md)

## 관련 테스트
- [test_type2_step_import_smoke.py](../../../tests/backend_em/test_type2_step_import_smoke.py.md)
- `tests/backend_em/test_aedt_sidecar_modeler.py`
- `tests/backend_em/test_aedt_sidecar_session.py`

## 변경 시 주의점
- Protocol 변경은 wrappers, proxies, fake sessions, pyright diagnostics를 함께 흔든다.
- PyAEDT version/API drift가 있으면 [0.2.22-type2-step-to-em-validate-pipeline](../../../../plans/0.2.22-type2-step-to-em-validate-pipeline.md)와 관련 tests를 같이 갱신한다.
