---
title: test_generate_type2_step.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 22:30
tags:
  - tests
  - type2
  - export
---

# test_generate_type2_step.py

## Source
- Path: `tests/type2/test_generate_type2_step.py`
- Code note path: `sdd/code/tests/type2/test_generate_type2_step.py.md`
- Direct owner: [[sdd/plans/0.2.22-type2-plate-stack-equivalent-3-slab]], [[sdd/plans/0.2.22-type2-plate-stack-z-usage-ratio]]
- Direct verification target: [[sdd/code/entry/generate_type2_step.py]]

## 역할
- type2 parser/export/ledger contract regression을 검증한다.

## Canonical coverage
- `tx_plate_stack` / `rx_plate_stack` parser acceptance
- active example loader expects shared TX/RX `pcb_total_thickness_mm = 0.4`
- object id mismatch / coil-only field rejection
- plate-stack `turn_count`, `metal_fill_factor`, `z_usage_ratio` validation plus explicit rejection of removed `shoe_depth_mm`
- TX/RX pre-unite baseline contract keeps per-turn/bridge/stub segment bodies; final handoff contract은
  role-level copper/ferrite role bodies로 정규화되며 6-body exact-name 순서를 유지한다.
- TX top-anchored `z_usage_ratio` Z window over full `tx_region` Y + `min_x` anchor
- RX bottom-anchored `z_usage_ratio` Z window over full `rx_region_max` Y + `min_x` anchor
- reduced-height plate-stack conductor/PCB/ferrite placement without shoe cutout bands
- plate-stack striped copper Z 배치는 pitch-slot centered placement를 검증한다.
- wall-side `N`, coil-side `N-1`, bridge `2N-2`, stub 2개 contract
- role별 단일 ferrite/copper group contract:
  - `g_copper_tx -> [tx_plate_copper]`, `g_ferrite_tx -> [tx_stack_pet_psa, tx_stack_ferrite, tx_stack_air]`
  - `g_copper_rx -> [rx_plate_copper]`, `g_ferrite_rx -> [rx_stack_pet_psa, rx_stack_ferrite, rx_stack_air]`
- plate-stack role에서 `g_copper_*` 또는 `g_ferrite_*` 누락/멤버 mismatch를 회귀 테스트로 반드시 잡는다.
- merged material ferrite-member ordering (`stack_pet_psa -> stack_ferrite -> stack_air`)
- plate-stack merged material body는 export-side unite 완료 후 label당 exactly one solid(`Solid`)로 유지
- plate-stack ferrite group member는 merged exact names 3개만 포함하고 그룹 순서는
  `stack_pet_psa -> stack_ferrite -> stack_air`를 유지
- plate-stack ferrite group object(`g_ferrite_tx`, `g_ferrite_rx`)의 child label order가 exact member order와 일치해야 한다.
- plate-stack export scene/ledger에 `*_stack_*_uN`/`SOLID*` label이 나타나면 contract 위반으로 간주한다.
- equivalent ferrite-family geometry는 X 순서와 두께를 직접 검증한다:
  `pcb_wall.max_x -> PET/PSA(1.5) -> ferrite(2.0) -> air(0.2) -> pcb_coil.min_x`.
- pre-unite 라벨(`*_copper_wall_t*`, `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_in/out`)이 exported/imported handoff body list에
  남아 있으면 즉시 실패로 본다.
- single-coil ferrite families(`tx_wall_*`, `under_rx_*`) export 시 동일 ferrite-group contract
- plate-stack `stub_port` terminal metadata + metadata-only reconstructed sheet geometry
- plate-stack terminal stubs and sheet metadata use the owner `min_y - 5.0 mm` plane for the left-side `-Y` endpoint.
- `terminal_metadata.input_stub_body_name`/`output_stub_body_name`은 pre-unite 라벨(`*_stub_in/out`)을 참조해야 하며
  imported final copper body명을 가리키면 안 된다.
- bridge contract regression:
  - bridge bbox X span은 full thickness가 아니라 interior span(`wall copper inner face -> coil copper inner face`)이어야 한다.
  - `tx_bridge_s*` / `rx_bridge_s*`는 wall/coil copper turns 및 notched slab bodies(`pcb_wall`, `pcb_coil`, `stack_pet_psa`, `stack_ferrite`, `stack_air`)와 positive-volume intersection이 없어야 한다.
  - same-edge neighboring bridges (`Y=max`끼리, `Y=min`끼리)도 positive-volume intersection이 없어야 한다.

## 변경 시 주의점
- active example role drift와 exact-name order drift를 같은 테스트 층에서 잡아야 한다.
- exact name/order drift 검사는 pre-unite segment contracts와 final export-contract(`6` final bodies per role)를 함께 검증해야 한다.
