---
title: type2_step_export.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - step-export
---

# type2_step_export.py

## Source
- Path: `src/peetsfea/type2_step_export.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_export.py.md`
- Status: active
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]
- Related feature plan: [[sdd/plans/0.2.23-type2-underlay-region-footprint-tx-gap-rx-support]]
- Related feature plan: [[sdd/plans/0.2.23-type2-tx-wall-parallel-ferrite-stack]]
- Parent note: [[sdd/code/entry/generate_type2_step.py]]

## 역할
- type2 scene export orchestration public API를 제공하고 entry CLI가 호출하는 thin library surface를 담당한다.
- full-scene export에서는 modeled single-coil scene children의 explicit body taxonomy를 그대로 내보내되, port sheet는 STEP child로 내보내지 않고 metadata-only ownership으로 유지한다.
- 0.2.23 document contract에서는 scene-layer가 추가한 explicit underlay tri-layer bodies를 TX/RX expected body set 뒤에 deterministic order로 내보낸다.
- export 시점 parsed `outputs`를 top-level step ledger retained handoff로 직렬화한다.

## 입력 / 출력
- 입력: TOML path, output dir, ledger path, seed
- 출력: exported scene artifacts and typed ledger result

## Canonical state
- module-level mutable state는 없다.
- canonical orchestration surface는 `export_type2_step_artifacts()` 한곳에 모은다.
- type2 export는 geometry/metadata뿐 아니라 report/output-variable retained contract도 step ledger에 고정한다.
- modeled export contract keeps port-sheet ownership in terminal metadata only; `tx_port_sheet` / `rx_port_sheet` are not STEP body names.
- role-aware expected body contract is underlay-aware:
  - single-layer TX base: `tx_pcb_l0`, `tx_copper_l0`
  - multilayer TX base: `tx_pcb_l{n}` + `tx_copper_stack`
  - TX underlay extension: append `tx_underlay_ferrite_u{n}`, `tx_underlay_pet_psa_u{n}`, `tx_underlay_air_u{n}` in semantic unit order
  - TX wall extension: append `tx_wall_ferrite_u{n}`, `tx_wall_pet_psa_u{n}`, `tx_wall_air_u{n}` after every `tx_underlay_*` exact body
  - RX base: `rx_pcb_l0`, `rx_copper_l0`
  - RX underlay extension: append `under_rx_ferrite_u{n}`, `under_rx_pet_psa_u{n}`, `under_rx_air_u{n}` in semantic unit order
- underlay exact object/body names must remain `<= 32` chars.
- direct export와 full-scene export 모두 같은 metadata-owned port-sheet geometry 규칙을 공유해야 한다.
- 그 bridge 규칙의 diagonal choice는 inter-stub centerline에 대해 더 넓어지는 diagonal, 즉 endpoint들의 perpendicular distance 합이 최대가 되는 diagonal이어야 한다.

## Invariants / fail-fast
- cleanup, spec parse, scene build, ledger write 순서가 deterministic해야 한다.
- `--ledger` replay를 위해 top-level `outputs` 직렬화는 export 시점 TOML contract를 lossless로 유지해야 한다.
- entry CLI는 내부 helper에 직접 접근하지 않고 이 facade를 통해서만 export한다.
- exact-name body sets must not resurrect `tx_port_sheet` / `rx_port_sheet` as STEP children.
- TX/RX underlay bodies are explicit solids, not spacing-only gaps and not non-model members.
- top-level scene children validation must stay body-taxonomy aware: each modeled child is one deterministic solid body with no mixed/multi-geometry fallback.
- direct modeled export must not leak single-square-owned or terminal-anchor-span port-sheet geometry from lower layers.
- direct modeled export must keep the same metadata-owned two-stub bridge geometry as full-scene export.
- underlay body naming/order drift changes import partition/material styling contracts and is therefore export-contract drift.
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
- role-aware underlay scene-layer assembly도 exact modeled body names/count contract의 일부이므로 import-side docs/tests와 lockstep으로 움직여야 한다.

## Links
- [[sdd/code/entry/generate_type2_step.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]
