---
title: type2_step_import_partition.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 00:45
tags:
  - hfss-import
  - partition
---

# type2_step_import_partition.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_partition.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py.md`
- Status: active
- Related feature plans: [[sdd/plans/0.2.22-type2-rx-plate-stack-striped-copper]], [[sdd/plans/0.2.22-type2-tx-rx-shared-plate-stack-import-only]], [[sdd/plans/0.2.22-type2-plate-stack-bridge-non-overlap-export]]

## 역할
- imported HFSS object names를 modeled/non-model ownership과 body-material families로 partition한다.

## 입력 / 출력
- 입력: validated step ledger, imported object names
- 출력: modeled object id별 imported names, non-model object id별 imported names, body-role grouping

## Canonical state
- TX plate families는 `tx_copper_wall_t*`, `tx_pcb_wall`, `tx_stack_*`, `tx_pcb_coil`, `tx_copper_coil_t*`, `tx_bridge_s*`, `tx_stub_*`를 분류한다.
- RX plate families는 `rx_copper_wall_t*`, `rx_pcb_wall`, `rx_stack_*`, `rx_pcb_coil`, `rx_copper_coil_t*`, `rx_bridge_s*`, `rx_stub_*`를 분류한다.
- shoe fill families는 active import partition contract에서 더 이상 지원하지 않는다. plate-stack underlay material families는 `*_stack_*`와 legacy single-coil underlay/wall prefixes만 허용한다.
- imported exact-name contract는 export ledger order와 동일한 label set을 요구한다.
- import partition은 exported non-overlap scene을 전제로 stable exact-name contract만 소비한다. geometry heal/repair/subtract ownership은 없다.
- runtime partition boundary는 exact exported label set/순서다. non-overlap 변경 이후에도 이름 안정성 contract를 그대로 유지한다.
- ferrite group contract는 role-family 기준 단일 그룹으로 고정한다: TX=`g_ferrite_tx`, RX=`g_ferrite_rx`.
- ferrite group members는 role별 ferrite/PET_PSA/vacuum body names를 export `expected_exported_body_names` 순서(평탄화된 creation order) 그대로 사용한다.

## Invariants / fail-fast
- modeled exact-name drift와 unclaimed imported object는 hard failure다.
- plate role body partition은 PCB 2장과 multi-body copper family를 유지해야 한다.
- stack ferrite/PET/air family와 single-coil underlay/wall ferrite family는 grouped export metadata와 exact-name member set/순서를 같이 유지해야 한다.
- export ledger가 shoe labels를 계속 내보내면 import partition은 unsupported name 또는 exact-name drift로 즉시 중단해야 한다.
- runtime에서 bridge/slab/copper intersection을 boolean으로 고치지 않는다. geometry 문제는 export-side contract violation로 취급한다.

## Collaborators
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 변경 시 주의점
- legacy coil naming family와 plate-stack naming family를 같은 prefix 규칙으로 뭉개지 않는다.
- `*_stub_in` / `*_stub_out`를 copper 분류에서 빼면 styling과 imported ledger contract가 동시에 깨진다.
- active plate-stack export contract는 shoe labels 없이 `*_stack_*`, PCB, copper-turn, bridge, stub labels만 유지해야 한다.
- name partition 흐름에 geometry repair fallback을 추가하지 않는다.
