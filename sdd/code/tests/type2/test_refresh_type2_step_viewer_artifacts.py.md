---
title: test_refresh_type2_step_viewer_artifacts.py
created: 2026-04-17 @ 09:09
updated: 2026-05-13 @ 00:00
tags:
  - step-export
---

# test_refresh_type2_step_viewer_artifacts.py

## Source
- Path: `tests/type2/test_refresh_type2_step_viewer_artifacts.py`
- Code note path: `sdd/code/tests/type2/test_refresh_type2_step_viewer_artifacts.py.md`
- Tested source: [refresh_type2_step_viewer_artifacts.py](../../entry/refresh_type2_step_viewer_artifacts.py.md)

## 역할
- viewer refresh input fixture인 active fixed example이 TxRx viewer/setup surface를 유지하는지 검증한다.
- fixed example에서 TX inner and RX modeled objects, TX output variables, and `TX_TML` EM references가 유지되는지
  검증한다.
- `notebooks/view_step_files.ipynb`가 notebook-local owner description dictionary 대신 TOML-backed description helper를 쓰는지 정적으로 검증한다.
- `notebooks/view_step_files.ipynb`가 removed TX outer canonical/raw owner mapping을 보유하지 않는지 정적으로 검증한다.
- `VIEW_INDEX`가 successful-entry list index가 아니라 manifest `sample_index`로 해석되는지 정적으로 검증한다.
- `VIEW_INDEX = -1` GUI build path가 sampled manifest selector를 호출하지 않고 fixed STEP ledger를 직접 setup-ready로 넘기는지 정적으로 검증한다.

## 입력 / 출력
- 입력:
- active `examples/type2_fixed.toml`
- `notebooks/view_step_files.ipynb`
- 출력:
  - parsed fixed example assertions
  - static notebook helper assertions

## Canonical state
- active fixed example TOML payload가 canonical assertion surface다.
- viewer notebook owner description text must come from TOML metadata through `type2_range_owner_descriptions`.
- viewer notebook sampled-value extraction must use active owner paths directly and must not retain TX outer canonical-to-raw lookup state.
- viewer notebook sampled manifest selection must use `entry["sample_index"]` matching so skipped samples cannot shift the Ansys GUI debug target.
- viewer notebook fixed GUI build must use `TYPE2_FIXED_LEDGER_PATH` and `setup_type2_step_ledger_into_hfss()` directly because fixed view mode has no sampled manifest entry.
- fixed viewer fixture keeps `tv_aluminum_plate` as sheet metadata and must not expect it as an exported STEP solid.

## Invariants / fail-fast
- fixed example keeps `tx_region` as guide context and derives `tx_inner_region` geometry context.
- fixed example keeps `tx_inner_rect_void_coil` as the active TX inner modeled input with fixed 1-repeat actual-region underlay and fixed disabled void stack.
- fixed example keeps `rx_region_max` and the RX modeled object as active EM geometry inputs.
- fixed example keeps `tv` as a non-modeled owner and `tv_aluminum_plate` as modeled aluminum sheet metadata sourced by `source_non_model_object_id = "tv"`.
- fixed example declares `tv_aluminum_plate.primitive = "sheet"` and `sheet_present = [true, 1, 1, 1]`; no viewer/setup expectation may require an exported `tv_aluminum_plate` solid.
- fixed example has TxRx outputs with TX variables and output expressions referencing `TX_TML`.
- viewer notebook must not contain `_OWNER_DESCRIPTIONS`; it must import and call `type2_range_owner_descriptions`.
- viewer notebook must not contain the removed canonical-to-raw owner mapping for
  `modeled_objects.tx_outer_rect_void_coil.x_position_ratio` or
  `modeled_objects.tx_inner_rect_void_coil.tx_outer_x_position_ratio`.
- viewer notebook sampled-value extraction must bind `source_path = owner_path` directly after removal of the raw-source alias helper.

## 직접 의존
- [type2-em-report-contract](../../../architecture/type2-em-report-contract.md)
- [0.2.24-type2-rxonly-tx-removal](../../../plans/0.2.24-type2-rxonly-tx-removal.md)
- [0.2.24-type2-range-owner-descriptions](../../../plans/0.2.24-type2-range-owner-descriptions.md)
- [0.2.24-view-step-derived-owner-display](../../../plans/0.2.24-view-step-derived-owner-display.md)
- [0.2.25-type2-tv-aluminum-sheet-presence](../../../plans/0.2.25-type2-tv-aluminum-sheet-presence.md)

## 이 파일을 쓰는 곳
- default pure-Python regression suite.

## 관련 테스트
- This file is high-level active fixed example coverage for the viewer refresh input contract and static notebook helper coverage.

## 변경 시 주의점
- notebook refresh output layout must not be tested by editing notebooks in this worker scope.
- example type2 TOML의 modeled object registry or output mode가 바뀌면 TX inner/RX EM assertions를 같이 갱신한다.
- TOML assertions must check the raw `source_non_model_object_id` field; backend ledgers translate that source into `placement_owner_id`.
- removed canonical-to-raw notebook checks are intentionally static because this worker does not own notebook edits or generated sampled TOML artifacts.
- notebook sample-index selector checks are static and must not execute AEDT.
