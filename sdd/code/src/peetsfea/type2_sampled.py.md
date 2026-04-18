---
title: type2_sampled.py
created: 2026-04-18 @ 09:09
updated: 2026-04-19 @ 21:42
tags:
  - sampling
  - build
---

# type2_sampled.py

## Source
- Path: `src/peetsfea/type2_sampled.py`
- Code note path: `sdd/code/src/peetsfea/type2_sampled.py.md`
- Status: active
- Related feature plans: [[sdd/plans/0.2.23-type2-sampled-build-split]], [[sdd/plans/0.2.25-type2-tx-rx-shared-plate-stack-import-only]]

## 역할
- type2 sampled owner-path selection, frozen sampled TOML rendering, manifest/build planning을 담당한다.

## 입력 / 출력
- 입력: source type2 TOML, seed range, manifest/sampled path
- 출력: sampled TOML, manifest entries, prepared build metadata

## Canonical state
- sampled owner canonical path는 `modeled_objects.<object_id>.<field>`다.
- active `tx_plate_stack`와 `rx_plate_stack`는 sampled owner를 갖지 않는다.
- active plate role scalar fields는 sampled TOML에 fixed scalar 그대로 복제된다.
- build path planning은 여전히 `run/sampled/type2/<design_id>/` layout을 쓴다.

## Invariants / fail-fast
- sampled metadata owner list는 source exportable sampled owner set과 exact match여야 한다.
- plate roles에서 coil-only sampled field assert를 요구하면 안 된다.
- active plate role fixed scalar fields는 sampled owner list에 나타나면 안 된다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_runtime.py]]
- [[sdd/code/entry/build.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_sample_type2_entry.py]]
- [[sdd/code/tests/type2/test_build_type2_entry.py]]

## 변경 시 주의점
- sampled path ownership을 role-blind single-coil field enumeration으로 되돌리지 않는다.
- active example role 교체와 sampled owner list expectations를 같이 갱신해야 한다.
