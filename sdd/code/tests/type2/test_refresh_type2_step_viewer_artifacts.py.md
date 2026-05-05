---
title: test_refresh_type2_step_viewer_artifacts.py
created: 2026-04-17 @ 09:09
updated: 2026-05-03 @ 21:30
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
- `notebooks/view_step_files.ipynb`가 canonical sampled owner label
  `modeled_objects.tx_outer_rect_void_coil.x_position_ratio`를 출력하면서 raw TOML source
  `modeled_objects.tx_inner_rect_void_coil.tx_outer_x_position_ratio`에서 값을 읽는 explicit mapping을 보유하는지 정적으로 검증한다.
- `VIEW_INDEX`가 successful-entry list index가 아니라 manifest `sample_index`로 해석되는지 정적으로 검증한다.

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
- viewer notebook sampled-value extraction must keep canonical owner paths as printed labels and use explicit canonical-to-raw mapping only for raw TOML lookup.
- viewer notebook sampled manifest selection must use `entry["sample_index"]` matching so skipped samples cannot shift the Ansys GUI debug target.

## Invariants / fail-fast
- fixed example keeps `tx_region` as guide context and derives `tx_inner_region` geometry context.
- fixed example keeps `tx_inner_rect_void_coil` as the active TX inner modeled input with fixed 4-repeat actual-region underlay.
- fixed example keeps `rx_region_max` and the RX modeled object as active EM geometry inputs.
- fixed example has TxRx outputs with TX variables and output expressions referencing `TX_TML`.
- viewer notebook must not contain `_OWNER_DESCRIPTIONS`; it must import and call `type2_range_owner_descriptions`.
- viewer notebook must contain the canonical-to-raw owner mapping for
  `modeled_objects.tx_outer_rect_void_coil.x_position_ratio` ->
  `modeled_objects.tx_inner_rect_void_coil.tx_outer_x_position_ratio`, and must still print the canonical
  `owner_path` together with TOML-backed descriptions.

## 직접 의존
- [type2-em-report-contract](../../../architecture/type2-em-report-contract.md)
- [0.2.24-type2-rxonly-tx-removal](../../../plans/0.2.24-type2-rxonly-tx-removal.md)
- [0.2.24-type2-range-owner-descriptions](../../../plans/0.2.24-type2-range-owner-descriptions.md)
- [0.2.24-view-step-derived-owner-display](../../../plans/0.2.24-view-step-derived-owner-display.md)

## 이 파일을 쓰는 곳
- default pure-Python regression suite.

## 관련 테스트
- This file is high-level active fixed example coverage for the viewer refresh input contract and static notebook helper coverage.

## 변경 시 주의점
- notebook refresh output layout must not be tested by editing notebooks in this worker scope.
- example type2 TOML의 modeled object registry or output mode가 바뀌면 TX inner/RX EM assertions를 같이 갱신한다.
- canonical-to-raw notebook checks are intentionally static because this worker does not own notebook edits or generated sampled TOML artifacts.
- notebook sample-index selector checks are static and must not execute AEDT.
