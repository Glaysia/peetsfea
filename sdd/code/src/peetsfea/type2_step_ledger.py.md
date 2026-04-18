---
title: type2_step_ledger.py
created: 2026-04-17 @ 09:09
updated: 2026-04-19 @ 00:25
tags:
  - step-export
---

# type2_step_ledger.py

## Source
- Path: `src/peetsfea/type2_step_ledger.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_ledger.py.md`
- Status: planned split target; source file is not created yet.
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]
- Related feature plan: [[sdd/plans/0.2.23-type2-underlay-region-footprint-tx-gap-rx-support]]
- Related feature plan: [[sdd/plans/0.2.23-type2-ferrite-underlay-equivalent-thickness]]
- Parent note: [[sdd/code/entry/generate_type2_step.py]]

## 역할
- type2 scene export 결과를 retained metadata ledger와 per-modeled metadata JSON으로 직렬화한다.

## 입력 / 출력
- 입력: parsed specs, scene assembly output, modeled export metadata, output directory
- 출력: `type2_step_ledger.json`, modeled source metadata JSON, canonical coordinate payloads

## Canonical state
- canonical artifact handoff는 top-level ledger의 `scene_step_path`와 object-level metadata entries다.
- canonical retained boundary-policy field는 top-level `em_policy`다.
- canonical retained report contract는 top-level `outputs`다.
- boundary handoff contract는 `type2_step_ledger.em_policy.radiation_margin_mm`를 기준으로 문서화한다.
- role-aware underlay ownership은 별도 ledger subtree가 아니라 modeled metadata의 exact `expected_exported_body_names` / `expected_exported_body_count` 계약에 포함된다.
- `underlay_repeat_count` source of truth는 input TOML이고, ledger는 resolved explicit body-name taxonomy만 보존한다. effective thickness multiplier meaning is not duplicated into the ledger.
- TX-only `underlay_gap_mm` source of truth도 input TOML에 두고, ledger는 gap value를 duplicated runtime state로 보존하지 않는다.

## Invariants / fail-fast
- modeled object metadata는 expected body names/count, canonical coordinates, terminal metadata를 모두 가져야 한다.
- TX underlay가 존재하면 modeled metadata expected body names/count는 collapsed effective trio `tx_underlay_ferrite_u0`, `tx_underlay_pet_psa_u0`, `tx_underlay_air_u0` order를 lossless로 보존해야 한다.
- RX underlay가 존재하면 modeled metadata expected body names/count는 collapsed effective trio `under_rx_ferrite_u0`, `under_rx_pet_psa_u0`, `under_rx_air_u0` order를 lossless로 보존해야 한다.
- canonical ledger schema docs는 top-level `scene_step_path`, `em_policy`, `outputs`, `non_model_objects`, `modeled_objects`를 함께 유지한다.
- ledger shape mismatch or missing owner/member metadata is a hard failure.
- `outputs` missing or malformed retained contract is a hard failure for downstream setup-ready replay.

## 직접 의존
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/type2_step_export.py]]
- downstream import path documented by [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]
- [[sdd/code/tests/type2/test_import_type2_step_entry.py]]

## 변경 시 주의점
- ledger shape를 바꾸면 import adapter, tests, notebooks를 같이 바꿔야 한다.
- canonical docs는 policy key를 `em_policy`로 고정한다. importer가 `import_time_policy`를 기대하는 현재 runtime mismatch는 문서 fallback이 아니라 후속 코드 수정으로 해소해야 한다.
- scene writing concern을 여기로 다시 끌어오지 않는다.
- `underlay_repeat_count` / `underlay_gap_mm`를 ledger-owned duplicated runtime state로 만들지 않는다. exact body names/count contract 하나만 canonical handoff로 유지한다.

## Links
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_pipeline.py]]
