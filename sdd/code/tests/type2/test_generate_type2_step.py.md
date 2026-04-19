---
title: test_generate_type2_step.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 02:26
tags:
  - tests
  - type2
  - export
---

# test_generate_type2_step.py

## Source
- Path: `tests/type2/test_generate_type2_step.py`
- Code note path: `sdd/code/tests/type2/test_generate_type2_step.py.md`
- Direct owner: [[sdd/plans/0.2.22-type2-remove-plate-stack-shoe-contract]]
- Direct verification target: [[sdd/code/entry/generate_type2_step.py]]

## 역할
- type2 parser/export/ledger contract regression을 검증한다.

## Canonical coverage
- `tx_plate_stack` / `rx_plate_stack` parser acceptance
- active example loader expects shared TX/RX `pcb_total_thickness_mm = 0.4`
- object id mismatch / coil-only field rejection
- plate-stack `turn_count`, `metal_fill_factor` validation plus explicit rejection of removed `shoe_depth_mm`
- TX/RX exact no-shoe baseline contract (`16` bodies each)
- TX full `tx_region` YZ + `min_x` anchor
- RX full `rx_region_max` YZ + `min_x` anchor
- full-height plate-stack conductor/PCB placement without shoe cutout bands
- wall-side `N`, coil-side `N-1`, bridge `2N-2`, stub 2개 contract
- role별 단일 ferrite group contract:
  TX `g_ferrite_tx`, RX `g_ferrite_rx`
- merged material ferrite-member ordering (`stack_pet_psa -> stack_ferrite -> stack_air`)
- plate-stack merged material body는 export-side unite 완료 후 label당 exactly one solid(`Solid`)로 유지
- plate-stack ferrite group member는 merged exact names 3개만 포함하고 그룹 순서는
  `stack_pet_psa -> stack_ferrite -> stack_air`를 유지
- plate-stack ferrite group object(`g_ferrite_tx`, `g_ferrite_rx`)의 child label order가 exact member order와 일치해야 한다.
- plate-stack export scene에 `*_stack_*_uN`/`SOLID*` label이 나타나면 contract 위반으로 간주한다.
- united ferrite-family geometry는 각 merged body의 X-span이 `pcb_wall.max_x -> pcb_coil.min_x` 전체 구간과 일치해야 한다.
- single-coil ferrite families(`tx_wall_*`, `under_rx_*`) export 시 동일 ferrite-group contract
- plate-stack `stub_port` terminal metadata + metadata-only reconstructed sheet geometry
- bridge contract regression:
  - bridge bbox X span은 full thickness가 아니라 interior span(`wall copper inner face -> coil copper inner face`)이어야 한다.
  - `tx_bridge_s*` / `rx_bridge_s*`는 wall/coil copper turns 및 notched slab bodies(`pcb_wall`, `pcb_coil`, `stack_pet_psa`, `stack_ferrite`, `stack_air`)와 positive-volume intersection이 없어야 한다.

## 변경 시 주의점
- active example role drift와 exact-name order drift를 같은 테스트 층에서 잡아야 한다.
- exact body name/order/count(`16`) contract와 merged stack united-one-solid shape contract를 함께 검증해야 한다.
