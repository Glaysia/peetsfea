---
title: type2_step_import_partition.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 02:01
tags:
  - hfss-import
  - partition
---

# type2_step_import_partition.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_partition.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py.md`
- Status: active

## Ownership
- Primary plan: [[sdd/plans/0.2.22-type2-plate-stack-material-merge]]
- Primary architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- imported HFSS object names를 modeled/non-model ownership과 body-material families로 partition한다.

## 입력 / 출력
- 입력: validated step ledger, imported object names
- 출력: modeled object id별 imported names, non-model object id별 imported names, body-role grouping

## Canonical state
- TX/RX final plate families는 role 수준의 united copper/PCB/merged stack bodies만 분류한다.
  - TX: `tx_plate_copper`, `tx_pcb_wall`, `tx_stack_pet_psa`, `tx_stack_ferrite`, `tx_stack_air`, `tx_pcb_coil`
  - RX: `rx_plate_copper`, `rx_pcb_wall`, `rx_stack_pet_psa`, `rx_stack_ferrite`, `rx_stack_air`, `rx_pcb_coil`
- `tx_copper_wall_t*`, `tx_copper_coil_t*`, `tx_bridge_s*`, `tx_stub_*`,
  `rx_copper_wall_t*`, `rx_copper_coil_t*`, `rx_bridge_s*`, `rx_stub_*`는 export-side
  pre-unite segment provenance only이며 final imported conductor가 아니다.
- shoe fill families는 active import partition contract에서 더 이상 지원하지 않는다. plate-stack ferrite-family는 merged exact-name 3-body만 허용하며 legacy single-coil underlay/wall prefixes는 single-coil path에만 남긴다.
- imported exact-name contract는 final export ledger order와 동일한 label set을 요구한다.
- plate-stack은 최종적으로 `tx_plate_copper`/`rx_plate_copper` 한 body를 각각 만들고,
  `g_copper_tx`/`g_copper_rx` 및 `g_ferrite_tx`/`g_ferrite_rx` 그룹으로 재구성한다.
- import partition은 exported non-overlap scene을 전제로 stable exact-name contract만 소비한다. geometry heal/repair/subtract ownership은 없다.
- runtime partition boundary는 exact exported label set/순서다. non-overlap 변경 이후에도 이름 안정성 contract를 그대로 유지한다.
- ferrite group contract는 role-family 기준 단일 그룹으로 고정한다: TX=`g_ferrite_tx`, RX=`g_ferrite_rx`.
- 역할별 ferrite 멤버는 아래 3-body 순서다.
  - `TX`: `tx_stack_pet_psa`, `tx_stack_ferrite`, `tx_stack_air`
  - `RX`: `rx_stack_pet_psa`, `rx_stack_ferrite`, `rx_stack_air`
- plate-stack ferrite group members는 merged exact 3-body(`*_stack_pet_psa`, `*_stack_ferrite`, `*_stack_air`)만 허용하며 export `expected_exported_body_names` 순서를 그대로 사용한다.
- plate-stack expected names에서 ferrite-family는 merged exact 3-body만 허용한다. legacy `tx_underlay_*`/`tx_wall_*`/`under_rx_*` ferrite-family labels는 export contract violation으로 즉시 중단한다.
- copper/pcb/fr4/ferrite 구성원은 최종 소비 지점에서 TX/RX로 구분되어 role-local 정규화되며, plate-stack mesh/EM은
  `g_copper_tx`/`g_copper_rx`의 member를 사용한다.

## Invariants / fail-fast
- modeled exact-name drift와 unclaimed imported object는 hard failure다.
- plate role body partition은 merged ferrite-family 3-body(각 material 1개)를 exact-name으로 유지해야 한다.
- stack ferrite/PET/air family와 single-coil underlay/wall ferrite family는 grouped export metadata와 exact-name member set/순서를 같이 유지해야 한다.
- plate-stack role에서 legacy `tx_stack_*_uN` / `rx_stack_*_uN` labels는 unsupported name으로 즉시 중단한다.
- `g_copper_tx`/`g_copper_rx` 또는 `g_ferrite_tx`/`g_ferrite_rx` 누락은 즉시 실패한다.
- export ledger가 shoe labels를 계속 내보내면 import partition은 unsupported name 또는 exact-name drift로 즉시 중단해야 한다.
- runtime에서 bridge/slab/copper intersection을 boolean으로 고치지 않는다. geometry 문제는 export-side contract violation로 취급한다.
- import 결과에 generic `SOLID*` names가 나타나면 import rename/repair 없이 export-contract violation으로 즉시 중단한다.
- export-side legacy pre-unite segment labels(`*_copper_wall_t*`, `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_*`)가 final conductor로 남아 있으면 unsupported로 즉시 실패한다.
- `tx_plate_copper`, `rx_plate_copper` 누락 또는 `g_copper_tx`, `g_copper_rx` 미재생성은 fail-fast다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_plate_stack.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_ledger.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_core.py]]

## 관련 테스트
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 변경 시 주의점
- legacy coil naming family와 plate-stack naming family를 같은 prefix 규칙으로 뭉개지 않는다.
- `*_stub_in` / `*_stub_out`를 export-side segment provenance 분류에서 빼면 styling/ledger 재구성 계약이 깨질 수 있다.
- active plate-stack export contract는 shoe labels 없이 `*_stack_*`, PCB, role-local `*_plate_copper` labels만 유지해야 한다.
- name partition 흐름에 geometry repair fallback을 추가하지 않는다.
