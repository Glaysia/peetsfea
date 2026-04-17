---
title: test_refresh_type2_step_viewer_artifacts.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - type2
  - step-export
---

# test_refresh_type2_step_viewer_artifacts.py

## Source
- Path: `tests/type2/test_refresh_type2_step_viewer_artifacts.py`
- Code note path: `sdd/code/tests/type2/test_refresh_type2_step_viewer_artifacts.py.md`
- Tested source: [[sdd/code/entry/refresh_type2_step_viewer_artifacts.py]]

## 역할
- type2 STEP viewer refresh entry가 stale output dir를 지우고 fresh STEP artifacts를 다시 만드는지 검증한다.
- refreshed ledger와 canonical scene STEP가 TX/RX placement contract를 유지하는지 확인한다.

## 입력 / 출력
- 입력:
  - temp output dir with stale files
  - active `examples/type2_fixed.toml`
- 출력:
  - refreshed artifact files
  - parsed refreshed ledger assertions

## Canonical state
- refreshed output dir contents와 ledger JSON이 직접 assertion 대상이다.

## Invariants / fail-fast
- stale file/subdir는 refresh 후 남아 있으면 안 된다.
- `type2_step_ledger.json`, `type2_scene.step`, modeled metadata files가 다시 생성돼야 한다.
- stale `type2_combined_preview.step`와 `objects/` 디렉터리는 refresh 후 남아 있으면 안 된다.
- refreshed active example baseline must keep `tx_region.bottom == 0` after the scene Z rebase.
- TX는 centered/top-aligned contract를 유지해야 한다.
- RX는 centered Y + bottom Z + owner max-X contract를 유지해야 하며, rebased active example에서는 `rx_region_max.min_z == 139`를 그대로 써야 한다.

## 직접 의존
- [[sdd/code/entry/refresh_type2_step_viewer_artifacts.py]]

## 이 파일을 쓰는 곳
- default pure-Python regression suite.

## 관련 테스트
- This file is the direct test coverage for [[sdd/code/entry/refresh_type2_step_viewer_artifacts.py]].

## 변경 시 주의점
- notebook refresh output layout이 바뀌면 file existence assertions를 같이 갱신한다.
- example type2 TOML의 modeled object registry가 바뀌면 object id assertions를 같이 갱신한다.
