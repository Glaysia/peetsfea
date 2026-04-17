---
title: type2_step_export.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 20:08
tags:
  - type2
  - step-export
---

# type2_step_export.py

## Source
- Path: `src/peetsfea/type2_step_export.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_export.py.md`
- Status: active
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]
- Parent note: [[sdd/code/entry/generate_type2_step.py]]

## 역할
- type2 scene export orchestration public API를 제공하고 entry CLI가 호출하는 thin library surface를 담당한다.
- full-scene export에서는 modeled single-coil scene children에 포함된 `tx_port_sheet` / `rx_port_sheet`를 top-level STEP children으로 그대로 내보낸다.
- direct single-coil export도 lower-level exporter를 그대로 통과시키지 않고 scene-layer canonical port-sheet geometry를 재사용해 same-rule STEP를 기록한다.

## 입력 / 출력
- 입력: TOML path, output dir, ledger path, seed
- 출력: exported scene artifacts and typed ledger result

## Canonical state
- module-level mutable state는 없다.
- canonical orchestration surface는 `export_type2_step_artifacts()` 한곳에 모은다.
- modeled export contract includes one explicit port-sheet body per single-coil modeled object with exact names `tx_port_sheet` and `rx_port_sheet`.
- current type2 single-coil scene exports exactly two port sheets total, one TX and one RX.
- direct export와 full-scene export 모두 두 stub bottom-face square diagonal bridge 규칙을 공유해야 한다.
- 그 bridge 규칙의 diagonal choice는 inter-stub centerline에 대해 더 넓어지는 diagonal, 즉 endpoint들의 perpendicular distance 합이 최대가 되는 diagonal이어야 한다.

## Invariants / fail-fast
- cleanup, spec parse, scene build, ledger write 순서가 deterministic해야 한다.
- entry CLI는 내부 helper에 직접 접근하지 않고 이 facade를 통해서만 export한다.
- exact-name body sets must include the port sheet bodies without reclassifying them as non-model members.
- top-level scene children validation now accepts either exactly one solid body or exactly one sheet face per child; mixed/multi-geometry children are fail-fast.
- direct modeled export must not leak single-square-owned or terminal-anchor-span port-sheet geometry from lower layers.
- direct modeled export must keep the same two-stub bridge geometry as full-scene export for `tx_port_sheet` / `rx_port_sheet`.
- widened diagonal selection rule drift is export contract drift이므로 scene-layer rule 변경 없이 lower-level propagated sheet를 그대로 통과시키면 안 된다.

## 직접 의존
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/entry/generate_type2_step.py]]
- [[sdd/code/entry/refresh_type2_step_viewer_artifacts.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]
- [[sdd/code/tests/type2/test_refresh_type2_step_viewer_artifacts.py]]

## 변경 시 주의점
- CLI parsing을 다시 library orchestration에 섞지 않는다.
- tx-only convenience export와 full scene export의 public entrypoint를 명시적으로 분리한다.
- full scene export path and direct tx-only export path now intentionally share the same scene-layer port-sheet synthesis surface; geometry-rule changes must land here first.
- import-side docs/tests must move in lockstep if modeled exact body names gain `tx_port_sheet` / `rx_port_sheet`.

## Links
- [[sdd/code/entry/generate_type2_step.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]
