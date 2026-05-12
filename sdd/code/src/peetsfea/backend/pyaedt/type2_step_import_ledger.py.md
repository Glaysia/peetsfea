---
title: type2_step_import_ledger.py
created: 2026-04-18 @ 09:09
updated: 2026-05-13 @ 00:00
tags:
  - import
  - pyaedt
---

# type2_step_import_ledger.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_ledger.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py.md`
- Status: active
- Primary graph owner: [type2-step-import-boundary](../../../../../architecture/type2-step-import-boundary.md)

## 역할
- STEP import 결과를 imported ledger로 직렬화한다.
- STEP ledger loading validates artifact schema and file hashes before import proceeds.
- STEP ledger loading validates the v3 modeled-entry exported-body coordinate contract before AEDT import.
- 0.2.24 SDD 기준 RX ownership, geometry-only `tx_inner_single_coil` ownership, and non-modeled guide/context ownership을 문서화한다.

## 입력 / 출력
- 입력: export ledger, imported object names, ownership partition result
- 출력: `type2_imported_ledger.json`

## Canonical state
- Imported ledger records source paths, seed, imported ownership, and imported object names.
- Single-coil terminal metadata must use `kind = "single_coil_port_v1"` and carry canonical global-mm sheet vertices and integration-line endpoints.
- Source ledgers distinguish semantic modeled coordinates from imported-body validation coordinates; import code must not infer one from the other.
- Imported ledger does not own mesh, boundary, port, or report summary state.
- `tx_region` may appear as a non-modeled guide object; it is not TX modeled geometry.
- `tx_inner_single_coil` may appear as modeled geometry with `tx_inner_region` placement ownership.
- `tx_inner_single_coil` ferrite-family group validation includes both actual-region underlay members and void-stack members in the exact export order declared by the ledger.
- `tx_outer_single_coil` is not an active modeled ledger role; ledgers containing it fail validation before import.
- `tv_aluminum_plate` is a one-body modeled role owned by non-modeled member `tv`, with `plane = "YZ"`, `material = "aluminum"`, `model_state = true`, and no exported body groups or terminal metadata.

## Invariants / fail-fast
- Missing required RX imported bodies fail immediately.
- Source TOML or scene STEP hash mismatch fails immediately as stale/mixed artifact evidence.
- Missing or malformed `exported_body_canonical_coordinates` fails before AEDT import.
- Missing required `tx_inner_single_coil` imported bodies fail immediately when declared by the source ledger.
- Generic imported-name drift is a contract failure.
- RxOnly imported ledger may record geometry-only TX inner entries, but setup-ready must filter them before active EM input construction.
- Any source ledger that still declares `tx_outer_single_coil` fails fast as unsupported active Type2 state.
- Tx inner void-stack group/member ordering drift fails during step-ledger validation before AEDT import.
- `tv_aluminum_plate` ledgers fail immediately if the owner is not `tv`, the plane is not `YZ`, material/model state drift, the expected body list is not exactly `["tv_aluminum_plate"]`, groups are non-empty, or terminal metadata is non-empty.

## Graph links
- Primary owner: [type2-step-import-boundary](../../../../../architecture/type2-step-import-boundary.md)
- Direct handoff: [type2_step_import_core.py](type2_step_import_core.py.md)
- Exceptional artifact handoff: [type2_step_ledger.py](../../type2_step_ledger.py.md)
- Related plan: [0.2.24 Type2 TX Outer Void Stack](../../../../../plans/0.2.24-type2-tx-outer-void-stack.md)
- Related plan: [0.2.24 Type2 TV Aluminum Plate](../../../../../plans/0.2.24-type2-tv-aluminum-plate.md)
- Related plan: [0.2.25 Type2 Port Sheet Contract Rewrite](../../../../../plans/0.2.25-type2-port-sheet-contract-rewrite.md)
- Related plan: [0.2.25 Type2 Exported Body Bounds Import Validation](../../../../../plans/0.2.25-type2-exported-body-bounds-import-validation.md)
