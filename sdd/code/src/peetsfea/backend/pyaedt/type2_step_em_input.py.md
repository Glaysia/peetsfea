---
title: type2_step_em_input.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 21:47
tags:
  - hfss-import
  - em
---

# type2_step_em_input.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_em_input.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_input.py.md`
- Status: active
- Related feature plan: [[sdd/plans/0.2.25-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- imported coil objects와 assigned ports를 EM pipeline input으로 정리한다.

## 입력 / 출력
- 입력: imported ledger, `EmPorts`
- 출력: `EmPipelineInput`

## Canonical state
- current EM input helper는 coil conductor/endpoint semantics 전용이다.
- active plate roles는 EM endpoint를 만들지 않으므로 unsupported다.

## Invariants / fail-fast
- plate roles imported names에서 endpoint나 conductor group을 추론하지 않는다.
- unsupported rejection은 setup-ready/port helper와 의미를 맞춘다.

## Collaborators
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_setup_ready.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_port_assignment.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_setup_ready.py]]

## 변경 시 주의점
- active plate roles에 fake endpoint metadata를 넣어 EM pipeline으로 넘기지 않는다.

