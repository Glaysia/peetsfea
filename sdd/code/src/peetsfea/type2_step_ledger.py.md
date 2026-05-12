---
title: type2_step_ledger.py
created: 2026-04-18 @ 09:09
updated: 2026-05-13 @ 00:00
tags:
  - step-export
  - ledger
---

# type2_step_ledger.py

## Source
- Path: `src/peetsfea/type2_step_ledger.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_ledger.py.md`
- Status: active

## 역할
- STEP export handoff metadata를 JSON ledger로 직렬화한다.
- Ledger artifact identity includes schema/version plus source TOML and scene STEP SHA-256 hashes.
- 0.2.24 SDD 기준 RX modeled handoff와 non-modeled guide/context handoff만 active shape contract다.
- `tx_inner_region` member provenance carries creation-time TX reference-line ratios, centered Y usage ratio, and resolved Y-parallel line endpoints.
- `tx_inner_actual_region` member provenance uses `TxActualRegionProvenance` to carry the source guide id, modeled source id, selected usage ratios, resolved actual-region design outer-box bounds, and diagnostic physical modeled-body bounds.
- Active generated ledgers must not contain `tx_outer_region`, `tx_outer_single_coil`, or `tx_outer_actual_region`; legacy imported artifacts that contain those shapes are handled by backend fail-fast validation.

## 입력 / 출력
- 입력: exported RX modeled entries, non-modeled guide/context entries, EM policy
- 출력: `type2_step_ledger.json`

## Canonical state
- RX body names/counts/groups are exact export contract values.
- Single-coil port sheet coordinates are canonical only in `terminal_metadata.kind = "single_coil_port_v1"`.
- `tx_region` may be present as non-modeled future guide context.
- `tx_inner_region`, when present, records canonical coordinates plus `tx_reference_line` provenance instead of requiring downstream geometry inference.
- `tx_inner_actual_region`, when present, records canonical coordinates plus actual-region provenance instead of requiring downstream geometry inference; the actual-region bounds are the canonical/design outer-box bounds.
- Modeled TV plate entries are represented as one modeled body (`tv_aluminum_plate`) with `placement_owner_id = "tv"` and `material = "aluminum"`, with no modeled body groups.
- `tx_outer_region`, `tx_outer_rect_void_coil`, and `tx_outer_actual_region` are not active generated ledger members.
- `tx_region_actual` and TX modeled bodies are not required ledger entries for RxOnly.
- Mesh/boundary/port/report runtime summaries are not ledger-owned.

## Invariants / fail-fast
- Ledger body names must match exported names exactly.
- Import must reject ledgers whose recorded source TOML or scene STEP hash no longer matches the files on disk.
- RxOnly ledger must not require TX modeled bodies.
- `tx_inner_region` provenance is mandatory when that member is emitted.
- `tx_inner_actual_region` provenance is mandatory when that member is emitted.
- Active generated ledgers must omit `tx_outer_region`, `tx_outer_actual_region`, and `tx_outer_rect_void_coil`.
- Missing RX terminal metadata for RxOnly is a contract failure.

## Collaborators
- [type2_step_export.py](type2_step_export.py.md)
- [type2_step_import_ledger.py](backend/pyaedt/type2_step_import_ledger.py.md)
- [type2-em-report-contract](../../../architecture/type2-em-report-contract.md)
- [0.2.24 Type2 TX Actual Regions](../../../plans/0.2.24-type2-tx-actual-regions.md)
- [0.2.24 Type2 TX Outer Single Coil](../../../plans/0.2.24-type2-tx-outer-single-coil.md)
- [0.2.25 Type2 Port Sheet Contract Rewrite](../../../plans/0.2.25-type2-port-sheet-contract-rewrite.md)
